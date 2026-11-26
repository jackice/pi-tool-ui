import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/read-t0-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-readt0-') as directory:
    root = Path(directory)
    (root / 'short.txt').write_text('alpha\nbeta\ngamma\n')
    (root / 'empty.txt').write_text('')
    (root / 'long.txt').write_text(''.join(f'line {index}\n' for index in range(1, 2101)))
    (root / 'longline.txt').write_text('x' * 60000)
    (root / 'notice.txt').write_text('alpha\n[Showing lines 1-2 of 99. Use offset=3 to continue.]\ngamma\n')
    (root / 'large.txt').write_text(''.join(f'line{index:04d}-' + 'x' * 30 + '\n' for index in range(1, 1501)))
    (root / 'notes.md').write_text('# Title\n\n- item\n')
    (root / 'pixel.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='))
    (root / 'bad.png').write_bytes(b'not-a-png')
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text('{}')
    observed = {}
    for case in ('basic', 'range', 'eof', 'zero', 'empty', 'notice', 'truncated', 'longline', 'invalid_offset', 'fractional', 'bytes', 'markdown', 'image', 'corrupt', 'image_unsupported'):
        log = root / f'{case}.jsonl'
        env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
                   PI_CODING_AGENT_DIR=str(agent), PI_READ_CASE=case, PI_READ_VISION='1' if case != 'image_unsupported' else '0', PI_TOOL_UI_PROBE_LOG=str(log))
        capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                     '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'read',
                     'Run the local read'], env, root, b'READ_T0_DONE', b'READ_T0_PROBE', rows=50)
        events = [json.loads(line) for line in log.read_text().splitlines()]
        final = next(item for item in events if item.get('event') == 'result' and not item['partial'])
        text = '\n'.join(block.get('text', '') for block in final['content'] if block.get('type') == 'text')
        observed[case] = {'error': final['error'], 'args': final['args'], 'text': text,
                          'kinds': [block.get('type') for block in final['content']], 'details': final.get('details')}

    assert observed['basic']['text'] == 'alpha\nbeta\ngamma\n'
    assert observed['empty']['text'] == ''
    assert 'line 5' in observed['range']['text'] and 'line 8' not in observed['range']['text']
    assert observed['eof']['error'] is True and observed['eof']['text']
    assert '[Showing lines' in observed['notice']['text'] and 'Use offset=3' in observed['notice']['text']
    trunc = observed['truncated']['details']['truncation']
    assert trunc['truncatedBy'] == 'lines' and trunc['outputLines'] < trunc['totalLines'], trunc
    byte_trunc = observed['bytes']['details']['truncation']
    assert byte_trunc['truncatedBy'] == 'bytes', byte_trunc
    assert '# Title' in observed['markdown']['text']
    assert 'image' in observed['image']['kinds'], observed['image']['kinds']
    assert 'image' not in observed['corrupt']['kinds'] and observed['corrupt']['text'], observed['corrupt']
    assert 'image' in observed['image_unsupported']['kinds'] and 'Read image file' in observed['image_unsupported']['text'], observed['image_unsupported']
    assert observed['invalid_offset']['error'] is True or observed['invalid_offset']['text']
    assert observed['fractional']['args']

    longline = observed['longline']['details']['truncation']
    assert longline['firstLineExceedsLimit'] is True, {k: v for k, v in longline.items() if k != 'content'}
    evidence = repo / 'docs/evidence/read-t0.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'cases': {case: {'error': item['error'], 'args': item['args'], 'kinds': item['kinds'], 'text_head': item['text'][:200],
                         'truncation': (item.get('details') or {}).get('truncation') and
                         {key: value for key, value in item['details']['truncation'].items() if key != 'content'}}
                  for case, item in observed.items()},
    }, ensure_ascii=False, indent=2) + '\n')
    print('Read T0：基础/范围/EOF/limit=0/空/同形 notice/行截断/超长首行已采集')
