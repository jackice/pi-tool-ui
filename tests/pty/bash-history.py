import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/bash-cases-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-history-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text('{}')
    session = root / 'session.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE='success',
               PI_TOOL_UI_PROBE_LOG=str(root / 'create.log'))
    subprocess.run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                    '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash', '--print', 'Run'],
                   cwd=root, env=env, capture_output=True, text=True, timeout=60, check=True)
    assert session.is_file()

    def replay(session_path, log_name):
        log = root / log_name
        capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session_path),
                     '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash', 'Run'],
                    dict(env, PI_TOOL_UI_PROBE_LOG=str(log)), root, b'BASH_PROBE', b'BASH_PROBE')
        events = [json.loads(line) for line in log.read_text().splitlines()]
        results = [item for item in events if item.get('event') == 'result' and not item['partial']]
        assert results, events
        return results[-1]

    fresh = replay(session, 'fresh.log')
    assert isinstance(fresh['durationMs'], (int, float)), fresh['durationMs']

    old = root / 'old-session.jsonl'
    lines = []
    for line in session.read_text().splitlines():
        entry = json.loads(line)
        message = entry.get('message')
        if entry.get('type') == 'message' and isinstance(message, dict) and message.get('role') == 'toolResult':
            message.pop('durationMs', None)
        lines.append(json.dumps(entry))
    old.write_text('\n'.join(lines) + '\n')
    legacy = replay(old, 'legacy.log')
    assert legacy.get('durationMs') is None, legacy.get('durationMs')
    assert [block.get('text') for block in legacy['content'] if block.get('type') == 'text'] == ['ok\n']

    evidence = repo / 'docs/evidence/bash-history.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'fresh_durationMs': fresh['durationMs'],
        'legacy_durationMs_missing': True,
        'legacy_final_text': ['ok\n'],
        'fixture': 'toolResult.durationMs removed from real 1.6.0 session (pre-duration format)',
    }, ensure_ascii=False, indent=2) + '\n')
    print('Bash 历史回放：新会话有 duration；去掉 durationMs 的旧格式会话为 undefined')
