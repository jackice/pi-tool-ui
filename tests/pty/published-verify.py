import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from screen import extract_card
from terminal import capture_tui


pi = shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
spec = 'npm:@jackice/pi-tool-ui@0.1.0'
golden = (repo / 'tests/fixtures/migration/edit-native-0.5.1.txt').read_text().rstrip('\n')


def run(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-published-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    env = dict(PATH=os.environ['PATH'], HOME=directory, TERM='xterm-256color',
               PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0')
    output = run([pi, 'install', spec], root, env)
    settings = json.loads((agent / 'settings.json').read_text())
    assert spec in settings['packages'], settings
    modules = agent / 'npm/node_modules'
    package = modules / '@jackice/pi-tool-ui'
    manifest = json.loads((package / 'package.json').read_text())
    assert manifest['version'] == '0.1.0'
    assert manifest['dependencies']['@jackice/pi-ui'] == '0.5.1'
    assert not (modules / '@earendil-works').exists(), '受管安装树含 Pi runtime'

    settings['toolUi'] = {'enabled': True, 'tools': {'edit': {'enabled': True}, 'hashline': {'enabled': True}}}
    (agent / 'settings.json').write_text(json.dumps(settings, ensure_ascii=False, indent=2))
    (root / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
    provider = repo / 'tests/pty/edit-provider.ts'
    screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                          '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'edit',
                          'Run the local edit'], dict(env, PI_TOOL_UI_PROBE_LOG=str(root / 'events.jsonl')),
                         root, b'BASELINE_DONE', b'BASELINE_DONE')
    card = '\n'.join(extract_card(screen, root))
    assert card == golden, card
    assert (root / 'notes.txt').read_text() == 'alpha\nbeta2\ngamma\n'
    evidence = repo / 'docs/evidence/published-install.json'
    evidence.write_text(json.dumps({
        'spec': spec,
        'installed_version': '0.1.0',
        'pi_ui': '0.5.1',
        'pi_runtime_in_tree': False,
        'card_matches_golden': True,
    }, ensure_ascii=False, indent=2) + '\n')
    print('npm 发布安装：pi install 成功，卡片与 golden 一致，无第二套 Pi runtime')
