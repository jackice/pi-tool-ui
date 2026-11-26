import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from screen import extract_card, render
from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/read-t0-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-readview-') as directory:
    root = Path(directory)
    (root / 'short.txt').write_text('alpha\nbeta\ngamma\n')
    (root / 'long.txt').write_text(''.join(f'line {index}\n' for index in range(1, 2101)))
    (root / 'notes.md').write_text('# Title\n\n- item\n')
    (root / 'pixel.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='))
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'read': {'enabled': True}}},
    }))
    observed = {}
    for case in ('basic', 'truncated', 'markdown', 'image'):
        env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
                   PI_CODING_AGENT_DIR=str(agent), PI_READ_CASE=case, PI_READ_VISION='1',
                   PI_TOOL_UI_PROBE_LOG=str(root / f'{case}.log'), PI_TOOL_UI_PROBE_RENDER='0')
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                              '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'read',
                              'Run the local read'], env, root, b'READ_T0_DONE', b'READ_T0_DONE', rows=60)
        text = '\n'.join(render(screen))
        try:
            card = '\n'.join(extract_card(screen, root))
        except (ValueError, StopIteration):
            card = ''
        observed[case] = {'text': text, 'card': card}

    assert 'Read' in observed['basic']['card'] and '1' in observed['basic']['card'] and 'gamma' in observed['basic']['card']
    assert observed['basic']['text'].count('alpha') == 1, observed['basic']['text'][-500:]
    assert 'truncated' in observed['truncated']['card'], observed['truncated']['card'][-400:]
    assert '# Title' in observed['markdown']['card'], observed['markdown']['card'][-400:]
    assert 'Read' not in observed['image']['card'], observed['image']['card'][-400:]
    evidence = repo / 'docs/evidence/read-view.json'
    evidence.write_text(json.dumps({'pi_version': version, 'text_card': True, 'truncation_notice': True,
                                    'markdown_source': True, 'image_native': True}, ensure_ascii=False, indent=2) + '\n')
    print('ReadView 接线：文本编号/截断提示/Markdown 源码；图片走原生')
