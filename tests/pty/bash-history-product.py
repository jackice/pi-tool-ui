import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from screen import render
from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/bash-cases-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-history-product-') as directory:
    root = Path(directory)
    creator = root / 'creator'
    creator.mkdir()
    (creator / 'settings.json').write_text('{}')
    session = root / 'session.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(creator), PI_BASH_CASE='success', PI_TOOL_UI_PROBE_RENDER='0',
               PI_TOOL_UI_PROBE_LOG=str(root / 'create.log'))
    subprocess.run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                    '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash', '--print', 'Run'],
                   cwd=root, env=env, capture_output=True, text=True, timeout=60, check=True)

    lines = []
    for line in session.read_text().splitlines():
        entry = json.loads(line)
        message = entry.get('message')
        if entry.get('type') == 'message' and isinstance(message, dict) and message.get('role') == 'toolResult':
            message.pop('durationMs', None)
        lines.append(json.dumps(entry))
    legacy = root / 'legacy.jsonl'
    legacy.write_text('\n'.join(lines) + '\n')

    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'bash': {'enabled': True}}},
    }))
    cards = {}
    for name, path in (('fresh', session), ('legacy', legacy)):
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(path),
                              '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash', 'Run'],
                             dict(env, PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_RENDER='0',
                                  PI_TOOL_UI_PROBE_LOG=str(root / f'{name}.log')),
                             root, b'\xe2\x9c\x93', b'\xe2\x9c\x93')
        cards[name] = '\n'.join(render(screen))
    assert 'Bash' in cards['fresh'] and 'ms' in cards['fresh'], cards['fresh'][-500:]
    assert 'Bash' in cards['legacy'] and 'ms' not in cards['legacy'], cards['legacy'][-500:]
    evidence = repo / 'docs/evidence/bash-history-product.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'fresh_has_duration': True,
        'legacy_omits_duration': True,
    }, ensure_ascii=False, indent=2) + '\n')
    print('Bash 产品历史：新会话显示耗时，旧格式会话省略耗时，卡片均存在')
