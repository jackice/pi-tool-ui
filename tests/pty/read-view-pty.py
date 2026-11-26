import re
import base64
import json
import struct
import zlib
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
    (root / 'empty.txt').write_text('')
    (root / 'longline.txt').write_text('x' * 60000)
    (root / 'image-text.txt').write_text('Read image file [image/png]\n[Image omitted: test]\n')
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    (root / 'broken.png').write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)) + chunk(b'IDAT', b'\x78\x9cbroken-deflate') + chunk(b'IEND', b''))
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'read': {'enabled': True}}},
    }))
    observed = {}
    for case in ('basic', 'truncated', 'markdown', 'image', 'image_show_on', 'image_show_off', 'range', 'zero', 'empty', 'longline', 'negative_limit', 'image_unsupported', 'short_negative_limit', 'short_fractional_limit', 'text_like_image', 'process_fail'):
        probe = 'image' if case.startswith('image_show') else case
        settings = {'packages': [str(repo)], 'toolUi': {'enabled': True, 'tools': {'read': {'enabled': True}}}}
        if case.startswith('image_show'):
            settings['terminal'] = {'showImages': case == 'image_show_on'}
        (agent / 'settings.json').write_text(json.dumps(settings))
        env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
                   PI_CODING_AGENT_DIR=str(agent), PI_READ_CASE=probe, PI_READ_VISION='1' if case != 'image_unsupported' else '0',
                   PI_TOOL_UI_PROBE_LOG=str(root / f'{case}.log'), PI_TOOL_UI_PROBE_RENDER='0',
                   **({'TERM_PROGRAM': 'herdr'} if case.startswith('image_show') else {}))
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                              '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'read',
                              'Run the local read'], env, root, b'READ_T0_DONE', b'READ_T0_DONE', rows=60)
        text = '\n'.join(render(screen, lines=60))
        try:
            card = '\n'.join(extract_card(screen, root, lines=60))
        except (ValueError, StopIteration):
            card = ''
        observed[case] = {'text': text, 'card': card}

    assert 'Read' in observed['basic']['card'] and '1' in observed['basic']['card'] and 'gamma' in observed['basic']['card']
    assert observed['basic']['text'].count('alpha') == 1, observed['basic']['text'][-500:]
    assert 'truncated' in observed['truncated']['card'], observed['truncated']['card'][-400:]
    assert '# Title' in observed['markdown']['card'], observed['markdown']['card'][-400:]
    assert 'Read' not in observed['image']['card'] and 'png' in observed['image']['text'], observed['image']['text'][-400:]
    assert not observed['image_show_on']['card'] and '[image/png' not in observed['image_show_on']['text'], observed['image_show_on']['text'][-400:]
    assert 'Read' not in observed['image_show_off']['card'], observed['image_show_off']['text'][-400:]
    assert 'line 1' in observed['negative_limit']['card'] and 'line 13' not in observed['negative_limit']['card'], observed['negative_limit']['card'][-500:]
    assert len(observed['negative_limit']['card'].splitlines()) <= 30, observed['negative_limit']['card'][-500:]
    assert 'Read' not in observed['image_unsupported']['card'] and 'placeholder' in observed['image_unsupported']['text'], observed['image_unsupported']['text'][-600:]
    assert 'line 5' in observed['range']['card'] and '[2094 more lines' in observed['range']['card'], observed['range']['card'][-500:]
    assert not any(re.search(r'│\s*(?:8|9)\s+\[2094', line) for line in observed['range']['card'].splitlines()), observed['range']['card'][-500:]
    assert 'more lines' in observed['zero']['card'] and 'line 1' not in observed['zero']['card'], observed['zero']['card'][-500:]
    assert not re.search(r'│\s*\d+\s+\[2101', observed['zero']['card']), observed['zero']['card'][-500:]
    assert 'offset=-1' in observed['short_negative_limit']['card'] and not re.search(r'│\s*\d+\s+(?:alpha|beta|\[6)', observed['short_negative_limit']['card']), observed['short_negative_limit']['card'][-500:]
    assert 'offset=-0.5' in observed['short_fractional_limit']['card'] and not re.search(r'│\s*\d+\s+(?:alpha|beta|gamma|\[5)', observed['short_fractional_limit']['card']), observed['short_fractional_limit']['card'][-500:]
    assert 'alpha' not in observed['empty']['card'] and len(observed['empty']['card'].splitlines()) == 2, observed['empty']['card'][-400:]
    assert 'Line 1 is' in observed['longline']['card'], observed['longline']['card'][-500:]
    assert not any(re.search(r'│\s*1\s+\[Line', line) for line in observed['longline']['card'].splitlines()), observed['longline']['card'][-500:]
    assert 'Read image file' in observed['text_like_image']['card'], observed['text_like_image']['card'][-500:]
    assert not any(re.search(r'│\s*1\s+Read image file', line) for line in observed['text_like_image']['card'].splitlines()), observed['text_like_image']['card'][-500:]
    assert 'Image omitted' in observed['process_fail']['card'], observed['process_fail']['card'][-500:]
    assert not any(re.search(r'│\s*1\s+Read image file', line) for line in observed['process_fail']['card'].splitlines()), observed['process_fail']['card'][-500:]
    evidence = repo / 'docs/evidence/read-view.json'
    evidence.write_text(json.dumps({'pi_version': version, 'text_card': True, 'truncation_notice': True,
                                    'markdown_source': True, 'image_native': True,
                                    'range_notice_unnumbered': True, 'zero_notice_only': True,
                                    'empty_no_rows': True, 'longline_raw': True,
                                    'image_text_diagnostic_raw': True, 'show_images_no_read_card': True, 'unsupported_warning_native': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('ReadView 接线：文本编号/截断提示/Markdown 源码；图片走原生')
