import base64
import json
import re
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

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-read-ab-') as directory:
    root = Path(directory)
    (root / 'short.txt').write_text('alpha\nbeta\ngamma\n')
    (root / 'long.txt').write_text(''.join(f'line {index}\n' for index in range(1, 2101)))
    (root / 'pixel.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='))
    (root / 'empty.txt').write_text('')
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    (root / 'broken.png').write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)) + chunk(b'IDAT', b'\x78\x9cbroken-deflate') + chunk(b'IEND', b''))
    observed = {}
    for case in ('basic', 'truncated', 'image', 'range', 'zero', 'empty', 'process_fail'):
        for enabled in (False, True):
            work = root / f'{case}-{"on" if enabled else "off"}'
            work.mkdir()
            for name in ('short.txt', 'long.txt', 'pixel.png', 'empty.txt', 'broken.png'):
                shutil.copyfile(root / name, work / name)
            agent = work / 'agent'
            agent.mkdir()
            settings = {'packages': [str(repo)], 'toolUi': {'enabled': enabled, 'tools': {'read': {'enabled': enabled}}}}
            (agent / 'settings.json').write_text(json.dumps(settings))
            log = work / 'events.jsonl'
            env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
                       PI_CODING_AGENT_DIR=str(agent), PI_READ_CASE=case, PI_READ_VISION='1',
                       PI_TOOL_UI_PROBE_LOG=str(log), PI_TOOL_UI_PROBE_RENDER='0')
            screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                                  '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'read',
                                  '--session', str(work / 'session.jsonl'), 'Run the local read'],
                                 env, work, b'READ_T0_DONE', b'READ_T0_DONE', rows=60)
            events = [json.loads(line) for line in log.read_text().splitlines()]
            result = None
            session = work / 'session.jsonl'
            if session.exists():
                for line in session.read_text().splitlines():
                    entry = json.loads(line)
                    message = entry.get('message')
                    if entry.get('type') == 'message' and isinstance(message, dict) and message.get('role') == 'toolResult':
                        result = message
            text = '\n'.join(render(screen))
            try:
                card = '\n'.join(extract_card(screen, work))
            except (ValueError, StopIteration):
                card = ''
            observed[f'{case}-{"on" if enabled else "off"}'] = {
                'content': result.get('content') if result else None,
                'details': result.get('details') if result else None,
                'executions': sum(1 for item in events if item.get('event') == 'tool-execution'),
                'text': text,
                'card': card,
            }

    for case in ('basic', 'truncated', 'image', 'range', 'zero', 'empty', 'process_fail'):
        on = observed[f'{case}-on']; off = observed[f'{case}-off']
        assert on['content'] == off['content'] and on['details'] == off['details'], case
        assert on['executions'] == off['executions'] == 1, case
        if case == 'image':
            assert 'Read' not in on['card'], on['card'][:300]
        else:
            assert 'Read' in on['text'], on['text'][-600:]
            if case == 'process_fail':
                assert not any(re.search(r'│\s*\d+\s+Read image file', line) for line in on['text'].splitlines()), on['text'][-600:]
            if case == 'zero':
                assert not any(re.search(r'│\s*\d+\s+\[2101', line) for line in on['text'].splitlines()), on['text'][-600:]
        assert 'Read' not in off['card'], off['card'][:300]

    evidence = repo / 'docs/evidence/read-product-ab.json'
    evidence.write_text(json.dumps({'pi_version': version, 'content_details_equal': True, 'runs': 1,
                                    'card_on': True, 'card_off': False, 'image_native': True, 'range_zero_empty_fail': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('Read 产品 A/B：content/details 一致、各读一次；文本 ON 有卡片、图片/ OFF 无')
