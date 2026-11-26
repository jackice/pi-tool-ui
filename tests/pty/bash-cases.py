import hashlib
import json
import os
import subprocess
from pathlib import Path
import shutil
import tempfile

from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/bash-cases-provider.ts'

version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
cli = Path(subprocess.run(['realpath', pi], capture_output=True, text=True, check=True).stdout.strip())
cli_sha = hashlib.sha256(cli.read_bytes()).hexdigest()

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-bash-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text('{}')
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color',
               PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0')
    observed = {}
    for case in ('success', 'empty', 'nonzero', 'lines', 'bytes', 'longline', 'stream', 'trunc_timeout'):
        log = root / f'{case}.jsonl'
        capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                     '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash', 'Run the local bash'],
                    dict(env, PI_BASH_CASE=case, PI_TOOL_UI_PROBE_LOG=str(log),
                         PI_BASH_TIMEOUT='1' if case == 'trunc_timeout' else '0'), root,
                    b'BASH_DONE', b'BASH_PROBE')
        events = [json.loads(line) for line in log.read_text().splitlines()]
        final = next(item for item in events if item.get('event') == 'result' and not item['partial'])
        partials = [item for item in events if item.get('event') == 'result' and item['partial']]
        observed[case] = {'final': final, 'partial_count': len(partials), 'first_partial': partials[0] if partials else None}

    success = observed['success']['final']
    assert [block['text'] for block in success['content'] if block['type'] == 'text'] == ['ok\n']
    assert isinstance(success['durationMs'], (int, float))

    empty = observed['empty']['final']
    assert empty['content'] == [] or empty['content'][0].get('text', '').strip() in {'', '(no output)'}

    nonzero = observed['nonzero']['final']
    assert nonzero['error'] is True

    lines = observed['lines']['final']
    truncation = lines['details']['truncation']
    assert truncation['outputLines'] < truncation['totalLines'], truncation

    bytes_case = observed['bytes']['final']
    byte_trunc = bytes_case['details']['truncation']
    assert byte_trunc['truncatedBy'] == 'bytes', byte_trunc
    assert byte_trunc['totalLines'] < 2000 and byte_trunc['totalBytes'] > 51200, byte_trunc
    assert 50000 < byte_trunc['outputBytes'] <= 51200, {k: v for k, v in byte_trunc.items() if k != 'content'}

    longline = observed['longline']['final']
    trunc = longline['details']['truncation']
    assert trunc['truncatedBy'] == 'bytes' and trunc['lastLinePartial'] is True, {k: v for k, v in trunc.items() if k != 'content'}

    trunc_timeout = observed['trunc_timeout']['final']
    timeout_text = '\n'.join(block.get('text', '') for block in trunc_timeout['content'] if block.get('type') == 'text')
    assert trunc_timeout['error'] is True and 'timed out' in timeout_text.lower(), {'error': trunc_timeout['error'], 'text': timeout_text[:300]}

    stream = observed['stream']
    assert stream['partial_count'] >= 1, stream
    assert [block['text'] for block in stream['final']['content'] if block['type'] == 'text'] == ['first\nsecond\n']

    evidence = repo / 'docs/evidence/bash-cases.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    def text_of(event):
        return '\n'.join(block.get('text', '') for block in event['content'] if block.get('type') == 'text')

    def details_of(event):
        details = event.get('details') or {}
        truncation = details.get('truncation') or {}
        return {**{key: value for key, value in details.items() if key != 'truncation'},
                **({'truncation': {key: value for key, value in truncation.items() if key != 'content'}} if truncation else {})}

    summary = {}
    for case, value in observed.items():
        final = value['final']
        first = value['first_partial']
        summary[case] = {
            'partial_count': value['partial_count'],
            'first_partial_text': text_of(first)[:200] if first else None,
            'final_text': text_of(final)[:200],
            'final_tail': text_of(final)[-200:],
            'error': final['error'],
            'args': final['args'],
            'durationMs': final['durationMs'],
            'details': details_of(final),
        }
    assert all(item['first_partial_text'] in (None, '') for item in summary.values()), '首帧应为空'
    summary['pi'] = {'version': version, 'cli': str(cli), 'sha256': cli_sha}
    evidence.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print('Bash T0：成功/空/非零/行截断/字节截断/超长行/流式 partial 均已采集')
