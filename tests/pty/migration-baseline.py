import json
import os
import re
from pathlib import Path
import shutil
import tempfile

from screen import render
from terminal import capture_tui


pi = shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
extension = workspace / 'dotfiles/pi/.pi/agent/extensions/hashline-diff'
hashline = Path.home() / '.pi/agent/npm/node_modules/@jackice/hashline'
inventories = {
    '0.4.2': Path.home() / '.pi/agent/npm/node_modules/@jackice/pi-session-todo/node_modules/@jackice/pi-ui',
    '0.5.1': extension / 'node_modules/@jackice/pi-ui',
}
scenarios = {
    'edit-native': ('edit-provider.ts', 'BASELINE_DONE', ('edit',)),
    'hashline': ('hashline-provider.ts', 'BASELINE_HASHLINE_DONE', ('read', 'hashline')),
}
fixtures = workspace / 'pi-tool-ui/tests/fixtures/migration'


def card(output, root):
    frame = [line.replace(str(root), '<ROOT>').replace(str(Path(root).resolve()), '<ROOT>') for line in render(output)]
    start = max(index for index, line in enumerate(frame) if '╭─' in line)
    end = next(index for index in range(start, len(frame)) if frame[index].lstrip().startswith('╰'))
    card = [re.sub(r'· \d+(?:\.\d+)?m?s', '· <MS>', line) for line in frame[start:end + 1]]
    return [re.sub(r'─+', '─', line) if line.startswith(('╭', '╰')) else line for line in card]


def capture(version, root, provider, done, tools):
    agent = root / 'agent'
    target = agent / 'extensions/hashline-diff'
    shutil.copytree(extension, target, ignore=shutil.ignore_patterns('node_modules'))
    library = target / 'node_modules/@jackice/pi-ui'
    library.parent.mkdir(parents=True)
    shutil.copytree(inventories[version], library)
    actual = json.loads((library / 'package.json').read_text())['version']
    assert actual == version, (version, actual)
    shutil.copytree(hashline, agent / 'extensions/hashline')
    for native in ('pi-utils', 'pi-natives', 'pi-natives-darwin-arm64'):
        shutil.copytree(Path.home() / f'.pi/agent/npm/node_modules/@oh-my-pi/{native}',
                        agent / f'node_modules/@oh-my-pi/{native}')
    (agent / 'settings.json').write_text(json.dumps({'editDiff': {'nativeEdit': True}}))
    (root / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
    log = root / 'events.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color',
               PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0', PI_TOOL_UI_PROBE_LOG=str(log))
    command = [pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
               '-e', str(Path(__file__).with_name(provider).resolve()), '--model', 'tool-ui-probe/local',
               '--tools', ','.join(tools), 'Run the local edit']
    output = capture_tui(command, env, root, done.encode(), done.encode())
    events = [json.loads(line) for line in log.read_text().splitlines()]
    assert sum(item.get('event') == 'tool-execution' for item in events) == 1, events
    return card(output, root)


def differences(left, right):
    return {line for line in set(left) ^ set(right) if line}


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-baseline-') as directory:
    base = Path(directory)
    fixtures.mkdir(parents=True, exist_ok=True)
    for name, (provider, done, tools) in scenarios.items():
        frames = {}
        for version in inventories:
            root = base / f'{name}-{version.replace(".", "-")}'
            root.mkdir()
            frames[version] = capture(version, root, provider, done, tools)
            (fixtures / f'{name}-{version}.txt').write_text('\n'.join(frames[version]) + '\n')
        changed = differences(frames['0.4.2'], frames['0.5.1'])
        assert changed and all(re.search(r'│ [+\- ]?\d* [+\- ]?\d* ?│', line) for line in changed), changed
        print(f'{name}：冻结 0.4.2 与 0.5.1 两版卡片；差异仅为 0.5.x 行号 gutter 去重')
