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

    log = root / 'replay.log'
    capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                 '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash', 'Run'],
                dict(env, PI_TOOL_UI_PROBE_LOG=str(log)), root, b'BASH_PROBE', b'BASH_PROBE')
    events = [json.loads(line) for line in log.read_text().splitlines()]
    results = [item for item in events if item.get('event') == 'result' and not item['partial']]
    assert results, events
    replayed = results[-1]
    assert isinstance(replayed['durationMs'], (int, float)), replayed['durationMs']
    assert [block.get('text') for block in replayed['content'] if block.get('type') == 'text'] == ['ok\n']
    evidence = repo / 'docs/evidence/bash-history.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'durationMs': replayed['durationMs'],
        'missing_duration_sample': 'Pi 1.6.0 无法产生；旧历史未存储时 renderer 代码在 undefined 时省略',
        'final_text': ['ok\n'],
    }, ensure_ascii=False, indent=2) + '\n')
    print('Bash 历史回放：durationMs 可用，正文仍为 ok')
