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
hashline = Path.home() / '.pi/agent/npm/node_modules/@jackice/hashline'
fixtures = repo / 'tests/fixtures/migration'
scenarios = {
    'edit-native': ('edit-provider.ts', 'BASELINE_DONE', ('edit',)),
    'hashline': ('hashline-provider.ts', 'BASELINE_HASHLINE_DONE', ('read', 'hashline')),
}
goldens = {name: (fixtures / f'{name}-0.5.1.txt').read_text().rstrip('\n') for name in scenarios}


def capture(root, settings, provider, done, tools):
    agent = root / 'agent'
    shutil.copytree(hashline, agent / 'extensions/hashline')
    for native in ('pi-utils', 'pi-natives', 'pi-natives-darwin-arm64'):
        shutil.copytree(Path.home() / f'.pi/agent/npm/node_modules/@oh-my-pi/{native}',
                        agent / f'node_modules/@oh-my-pi/{native}')
    (agent / 'settings.json').write_text(json.dumps(settings))
    (root / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color',
               PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0',
               PI_TOOL_UI_PROBE_LOG=str(root / 'events.jsonl'))
    command = [pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
               '-e', str(Path(__file__).with_name(provider).resolve()), '--model', 'tool-ui-probe/local',
               '--tools', ','.join(tools), 'Run the local edit']
    return capture_tui(command, env, root, done.encode(), done.encode())


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-parity-') as directory:
    base = Path(directory)
    package = str(repo)
    for name, (provider, done, tools) in scenarios.items():
        root = base / f'on-{name}'
        root.mkdir()
        screen = capture(root, {'packages': [package], 'editDiff': {'nativeEdit': True}}, provider, done, tools)
        card = '\n'.join(extract_card(screen, root))
        assert card == goldens[name], f'{name} 与旧 golden 不一致:\n{card}'
        off = base / f'off-{name}'
        off.mkdir()
        screen = capture(off, {'packages': [package], 'toolUi': {'enabled': False}}, provider, done, tools)
        assert b'\xe2\x95\xad\xe2\x94\x80 Edit' not in screen, f'{name} 关闭后仍接管'
        print(f'{name}：旧配置映射后与 golden 一致；toolUi 关闭时保留原生渲染')
