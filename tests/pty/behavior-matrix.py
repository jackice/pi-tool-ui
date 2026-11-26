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
old = workspace / 'dotfiles/pi/.pi/agent/extensions/hashline-diff'
library = old / 'node_modules/@jackice/pi-ui'


def install_old(agent):
    shutil.copytree(old, agent / 'extensions/hashline-diff', ignore=shutil.ignore_patterns('node_modules'))
    (agent / 'extensions/hashline-diff/node_modules/@jackice').mkdir(parents=True)
    shutil.copytree(library, agent / 'extensions/hashline-diff/node_modules/@jackice/pi-ui')


def results(session):
    out = []
    for line in session.read_text().splitlines():
        entry = json.loads(line)
        message = entry.get('message', {})
        if entry.get('type') == 'message' and message.get('role') == 'toolResult':
            out.append([block.get('text', '') for block in message.get('content', [])])
    return out


def run_scenario(root, kind, extra=(), expand=False):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
    return_values = {}
    for name in ('old', 'new'):
        agent = root / f'{name}-agent'
        agent.mkdir()
        if name == 'old':
            install_old(agent)
            settings = {'editDiff': {'nativeEdit': True}}
        else:
            settings = {'packages': [str(repo)], 'editDiff': {'nativeEdit': True}}
        (agent / 'settings.json').write_text(json.dumps(settings))
        (root / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
        session = root / f'{name}-{kind}.jsonl'
        env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color',
                   PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0',
                   PI_TOOL_UI_PROBE_LOG=str(root / f'{name}-{kind}.log'))
        provider = repo / 'tests/pty' / ('edit-provider.ts' if kind != 'error' else 'edit-error-provider.ts')
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                              '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'edit',
                              *extra, 'Run the local edit'], env, root, b'BASELINE_DONE', b'BASELINE_DONE')
        return_values[name] = {
            'screen': screen,
            'results': results(session),
            'bytes': (root / 'notes.txt').read_bytes(),
        }
    return return_values


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-behavior-') as directory:
    base = Path(directory)
    for kind, extra in (('light', ('--use-theme', 'light')), ('error', ()), ('expanded', ())):
        root = base / kind
        values = run_scenario(root, kind, extra, expand=kind == 'expanded')
        if kind == 'error':
            assert b'\xe2\x95\xad\xe2\x94\x80 Edit' not in values['new']['screen'], '错误结果不应自绘卡片'
            old_card = new_card = 'native-error'
        else:
            old_card = '\n'.join(extract_card(values['old']['screen'], root))
            new_card = '\n'.join(extract_card(values['new']['screen'], root))
        assert values['old']['results'] == values['new']['results'], kind
        assert values['old']['bytes'] == values['new']['bytes'], kind
        if kind in ('light', 'expanded'):
            assert old_card == new_card, f'{kind} 卡片不同\n{old_card}\n---\n{new_card}'
        else:
            assert 'Could not find' in json.dumps(values['new']['results']), values['new']['results']
        print(f'{kind}：结果与文件字节一致；卡片 {"一致" if old_card == new_card else "走原生错误渲染"}')
    print('行为矩阵通过')
