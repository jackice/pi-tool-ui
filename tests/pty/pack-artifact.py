import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from screen import extract_card
from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
npm = shutil.which('npm')
assert pi and npm, '需要 Pi 1.6.0 与 npm'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
subprocess.run(['npm', 'run', 'build'], cwd=repo, check=True, capture_output=True, text=True)

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-artifact-') as directory:
    root = Path(directory)
    env = dict(PATH=os.environ['PATH'], HOME=directory, TERM='xterm-256color', PI_TELEMETRY='0',
               npm_config_cache=str(root / 'npm-cache'))
    packed = json.loads(subprocess.run([npm, 'pack', '--json', '--pack-destination', directory],
                                       cwd=repo, env=env, capture_output=True, text=True, check=True).stdout)[0]
    install = root / 'install'
    install.mkdir()
    subprocess.run([npm, 'install', '--legacy-peer-deps', '--ignore-scripts', '--no-audit', '--no-fund',
                    '--fetch-retries=0', '--fetch-timeout=20000', str(root / packed['filename'])],
                   cwd=install, env=env, capture_output=True, text=True, check=True)
    modules = install / 'node_modules'
    package = modules / '@jackice/pi-tool-ui'
    assert (package / 'dist/index.js').is_file()
    pi_ui = json.loads((modules / '@jackice/pi-ui/package.json').read_text())['version']
    assert pi_ui == '0.7.3', pi_ui
    assert not list(modules.rglob('@earendil-works/pi-*/package.json')), '安装树含第二套 Pi runtime'

    observed = {}
    for tool, provider, variable, done, marker in (
        ('write', repo / 'tests/pty/write-cases-provider.ts', 'PI_WRITE_CASE', b'WRITE_DONE', b'Write'),
        ('read', repo / 'tests/pty/read-t0-provider.ts', 'PI_READ_CASE', b'READ_T0_DONE', b'Read'),
        ('bash', repo / 'tests/pty/bash-cases-provider.ts', 'PI_BASH_CASE', b'BASH_DONE', b'Bash'),
    ):
        work = root / tool
        work.mkdir()
        (work / 'short.txt').write_text('alpha\nbeta\ngamma\n')
        agent = work / 'agent'
        agent.mkdir()
        (agent / 'settings.json').write_text(json.dumps({
            'packages': [str(package)],
            'toolUi': {'enabled': True, 'tools': {tool: {'enabled': True}}},
        }))
        case = 'success' if tool in ('write', 'bash') else 'basic'
        tool_env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
                        PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(work / 'events.jsonl'),
                        PI_TOOL_UI_PROBE_RENDER='0', **{variable: case})
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                              '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', tool,
                              'Run the local tool'], tool_env, work, done, marker, rows=60)
        assert b'Failed to load extension' not in screen, screen[-2000:]
        card = '\n'.join(extract_card(screen, work, lines=60))
        observed[tool] = card
    assert 'Write' in observed['write'] and 'alpha' in observed['write'], observed['write'][-500:]
    assert 'Read' in observed['read'] and 'gamma' in observed['read'], observed['read'][-500:]
    assert 'Bash' in observed['bash'] and 'ok' in observed['bash'], observed['bash'][-500:]
    evidence = repo / 'docs/evidence/pack-artifact.json'
    evidence.write_text(json.dumps({'package': 'pi-tool-ui-0.1.0.tgz', 'pi_ui': pi_ui,
                                    'pi_runtime_in_tree': False, 'write_card': True, 'read_card': True, 'bash_card': True,
                                    'clean_agent': True}, ensure_ascii=False, indent=2) + '\n')
    print('打包产物：干净安装 pi-tool-ui + pi-ui 0.7.3，无第二套 Pi runtime；Write/Read/Bash 卡片可用')
