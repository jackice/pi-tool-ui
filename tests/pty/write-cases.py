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
provider = repo / 'tests/pty/write-cases-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-write-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text('{}')
    (root / 'dir').mkdir()
    observed = {}
    for case in ('success', 'empty', 'unicode', 'overwrite', 'error'):
        work = root / case
        work.mkdir()
        (work / 'dir').mkdir()
        if case == 'overwrite':
            (work / 'out.txt').write_text('initial\n')
        log = work / 'events.jsonl'
        env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
                   PI_CODING_AGENT_DIR=str(agent), PI_WRITE_CASE=case, PI_TOOL_UI_PROBE_LOG=str(log))
        capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                     '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'write',
                     'Run the local write'], env, work, b'WRITE_DONE', b'WRITE_PROBE', rows=50)
        events = [json.loads(line) for line in log.read_text().splitlines()]
        final = next(item for item in events if item.get('event') == 'result' and not item['partial'])
        files = {path.name: path.read_bytes() for path in work.iterdir() if path.is_file() and path.suffix in {'.txt'}}
        observed[case] = {
            'error': final['error'],
            'args': final['args'],
            'text': [block.get('text', '') for block in final['content'] if block.get('type') == 'text'],
            'files': {name: data.decode() for name, data in files.items()},
            'executions': sum(1 for item in events if item.get('event') == 'tool-execution'),
        }

    assert observed['success']['files']['out.txt'] == 'alpha\nbeta\n'
    assert observed['empty']['files']['empty.txt'] == ''
    assert observed['unicode']['files']['unicode.txt'] == '中文🙂\nno trailing newline'
    assert observed['overwrite']['files']['out.txt'] == 'replaced\n'
    assert observed['error']['error'] is True and observed['error']['text']
    assert all(item['executions'] == 1 for item in observed.values())
    evidence = repo / 'docs/evidence/write-cases.json'
    evidence.write_text(json.dumps({'pi_version': version, **observed}, ensure_ascii=False, indent=2) + '\n')
    print('Write T0-W1/W2：成功/空/Unicode/覆盖/错误 bytes 与 final 已采集，各执行一次')
