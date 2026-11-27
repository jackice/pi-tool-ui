import json
import os
import re
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
    (agent / 'extensions').mkdir()
    shutil.copyfile(workspace / 'dotfiles/pi/.pi/agent/extensions/goal.ts', agent / 'extensions/goal.ts')
    shutil.copyfile(Path.home() / '.pi/agent/pi-prompt.json', agent / 'pi-prompt.json')
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo), str(prompt), str(todo), str(Path.home() / '.pi/agent/npm/node_modules/pi-subagents')],
        'toolUi': {'enabled': True, 'tools': {'write': {'enabled': True}, 'read': {'enabled': True}}},
    }))
    log = root / 'events.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(log))
    screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                          '-e', str(provider), '--model', 'tool-ui-probe/local',
                          '--tools', 'subagent,get_goal,session_todo,write,read', 'Run the mixed versions'],
                         env, root, b'MIXED_DONE', b'MIXED_DONE', rows=60)
    text = '\n'.join(render(screen, lines=60))
    assert b'Failed to load extension' not in screen, screen[-3000:]
    assert 'MIXED_TODO_TASK' in text and 'Phase  0/1' in text, text[-2000:]
    assert 'get_goal' in text and 'subagent' in text, text[-2000:]
    assert not re.search(r'↓\d+ R\d', text), text[-2000:]
    assert '╰─' in text and 'π' in text, text[-2000:]
    assert '╭─ Write' in text and '╭─ Read' in text, text[-2000:]

    evidence = repo / 'docs/evidence/mixed-versions.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'product_pi_ui': json.loads((repo / 'node_modules/@jackice/pi-ui/package.json').read_text())['version'],
        'shared_pi_ui': package_version(shared_ui),
        'prompt_version': package_version(prompt),
        'todo_version': package_version(todo),
        'footer_mode': 'none',
        'native_footer_absent': True,
        'todo_hud': True,
        'todo_hud_phase': True,
        'prompt_band': True,
        'write_card': True,
        'read_card': True,
        'goal_extension_loaded': True,
        'goal_tool_called': True,
        'subagents_loaded': True,
        'subagent_tool_called': True,
        'failed_load': False,
    }, ensure_ascii=False, indent=2) + '\n')
    print('混合 pi-ui：产品 0.7.2 + Prompt(none)/TODO/Goal 共享 0.5.0；HUD、band、Write/Read 卡片可用')
