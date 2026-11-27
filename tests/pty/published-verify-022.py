import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from screen import extract_card, render
from terminal import capture_tui


pi = shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
spec = 'npm:@jackice/pi-tool-ui@0.2.2'


def run(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-published-020-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    env = dict(PATH=os.environ['PATH'], HOME=directory, TERM='xterm-256color',
               PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0')
    run([pi, 'install', spec], root, env)
    settings = json.loads((agent / 'settings.json').read_text())
    assert spec in settings['packages'], settings
    modules = agent / 'npm/node_modules'
    package = modules / '@jackice/pi-tool-ui'
    manifest = json.loads((package / 'package.json').read_text())
    assert manifest['version'] == '0.2.2'
    readme = (package / 'README.md').read_text()
    assert '## 已知限制' in readme and 'R2/R3' in readme, '已发布 README 缺 known limitations'
    assert manifest['dependencies']['@jackice/pi-ui'] == '0.8.1'
    assert json.loads((modules / '@jackice/pi-ui/package.json').read_text())['version'] == '0.8.1'
    assert not (modules / '@earendil-works').exists(), '受管安装树含 Pi runtime'

    settings['toolUi'] = {'enabled': True, 'tools': {'write': {'enabled': True}, 'read': {'enabled': True}, 'bash': {'enabled': True}, 'edit': {'enabled': True}}}
    (agent / 'settings.json').write_text(json.dumps(settings, ensure_ascii=False, indent=2))
    (root / 'short.txt').write_text('alpha\nbeta\ngamma\n')
    (root / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
    observed = {}
    for tool, provider, variable, case, done, marker in (
        ('write', repo / 'tests/pty/write-cases-provider.ts', 'PI_WRITE_CASE', 'success', b'WRITE_DONE', b'Write'),
        ('read', repo / 'tests/pty/read-t0-provider.ts', 'PI_READ_CASE', 'basic', b'READ_T0_DONE', b'Read'),
        ('bash', repo / 'tests/pty/bash-cases-provider.ts', 'PI_BASH_CASE', 'success', b'BASH_DONE', b'Bash'),
        ('edit', repo / 'tests/pty/edit-provider.ts', 'PI_EDIT_CASE', '', b'BASELINE_DONE', b'Edit'),
    ):
        tool_env = dict(env, PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(root / f'{tool}.log'),
                        PI_TOOL_UI_PROBE_RENDER='0', **{variable: case})
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                              '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', tool,
                              'Run the local tool'], tool_env, root, done, marker, rows=60)
        assert b'Failed to load extension' not in screen, screen[-2000:]
        observed[tool] = '\n'.join(extract_card(screen, root, lines=60))
    assert 'Write' in observed['write'] and 'alpha' in observed['write'], observed['write'][-500:]
    assert 'Read' in observed['read'] and 'gamma' in observed['read'], observed['read'][-500:]
    assert 'Bash' in observed['bash'] and 'ok' in observed['bash'], observed['bash'][-500:]
    edit_golden = (repo / 'tests/fixtures/migration/edit-native-0.5.1.txt').read_text().rstrip('\n')
    assert observed['edit'] == edit_golden, observed['edit'][-800:]
    evidence = repo / 'docs/evidence/published-install-022.json'
    evidence.write_text(json.dumps({
        'spec': spec,
        'installed_version': '0.2.2',
        'pi_ui': '0.8.1',
        'pi_runtime_in_tree': False,
        'write_card': True,
        'readme_limitations': True,
        'read_card': True,
        'bash_card': True,
        'edit_card': True,
    }, ensure_ascii=False, indent=2) + '\n')
    print('npm 0.2.2：pi install 成功；Write/Read/Bash/Edit 卡片可用；安装树无 Pi runtime')
