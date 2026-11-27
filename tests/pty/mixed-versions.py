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
provider = repo / 'tests/pty/mixed-provider.ts'
managed = Path.home() / '.pi/agent/npm/node_modules/@jackice'
prompt = managed / 'pi-prompt'
todo = managed / 'pi-session-todo'
shared_ui = managed / 'pi-ui'


def package_version(path):
    return json.loads((path / 'package.json').read_text())['version']


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-mixed-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo), str(prompt), str(todo)],
        'toolUi': {'enabled': True, 'tools': {'write': {'enabled': True}, 'read': {'enabled': True}}},
    }))
    log = root / 'events.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(log))
    screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                          '-e', str(provider), '--model', 'tool-ui-probe/local',
                          '--tools', 'session_todo,write,read', 'Run the mixed versions'],
                         env, root, b'MIXED_DONE', b'MIXED_DONE', rows=60)
    text = '\n'.join(render(screen, lines=60))
    assert b'Failed to load extension' not in screen, screen[-3000:]
    assert 'MIXED_TODO_TASK' in text, text[-2000:]
    assert '╰─' in text, text[-2000:]
    assert '╭─ Write' in text and '╭─ Read' in text, text[-2000:]

    evidence = repo / 'docs/evidence/mixed-versions.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'product_pi_ui': json.loads((repo / 'node_modules/@jackice/pi-ui/package.json').read_text())['version'],
        'shared_pi_ui': package_version(shared_ui),
        'prompt_version': package_version(prompt),
        'todo_version': package_version(todo),
        'todo_hud': True,
        'prompt_band': True,
        'write_card': True,
        'read_card': True,
        'failed_load': False,
    }, ensure_ascii=False, indent=2) + '\n')
    print('混合 pi-ui：产品 0.7.2 + Prompt/TODO 共享 0.5.0，同时加载；HUD、band、Write/Read 卡片可用')
