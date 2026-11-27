import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shutil
import struct
import subprocess
import tempfile
import termios
import time


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
gate = workspace / 'pi-approval-gate'
provider = repo / 'tests/pty/bash-cases-provider.ts'


def interact(work, agent, action):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
    env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE='risky',
               PI_TOOL_UI_PROBE_LOG=str(work / 'events.jsonl'))
    command = [pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
               '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash',
               '--approval-timeout-ms', '900', '--approval-arm-ms', '100', 'Run the local bash']
    output = bytearray()
    count = work / 'count.txt'

    def wait_for(marker, start=0):
        deadline = time.monotonic() + 15
        while output.find(marker, start) < 0 and time.monotonic() < deadline:
            if select.select([master], [], [], 0.2)[0]:
                try:
                    output.extend(os.read(master, 65536))
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
        assert output.find(marker, start) >= 0, output[-3000:].decode(errors='replace')

    try:
        with subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=work, env=env) as process:
            os.close(slave)
            try:
                wait_for(b'navigate')
                assert not count.exists(), '批准前命令已执行'
                time.sleep(0.2)
                os.write(master, b'\r' if action == 'allow' else b'\x1b')
                wait_for(b'BASH_DONE')
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
    finally:
        os.close(master)
    events = [json.loads(line) for line in (work / 'events.jsonl').read_text().splitlines()]
    final = next(item for item in events if item.get('event') == 'result' and not item['partial'])
    return {
        'runs': len(count.read_text().splitlines()) if count.exists() else 0,
        'error': final['error'],
        'text': [block.get('text', '') for block in final['content']],
    }


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-secstack-') as directory:
    root = Path(directory)
    observed = {}
    for action in ('allow', 'deny'):
        work = root / action
        work.mkdir()
        agent = work / 'agent'
        (agent / 'extensions').mkdir(parents=True)
        shutil.copytree(gate, agent / 'extensions/approval-gate')
        (agent / 'settings.json').write_text(json.dumps({
            'packages': [str(repo)],
            'toolUi': {'enabled': True, 'tools': {'bash': {'enabled': True}}},
        }))
        observed[action] = interact(work, agent, action)
    assert observed['allow']['runs'] == 1 and observed['allow']['error'] is False
    assert observed['deny']['runs'] == 0 and observed['deny']['error'] is True
    assert 'Blocked by approval gate' in observed['deny']['text'][0]
    evidence = repo / 'docs/evidence/security-stack.json'
    evidence.write_text(json.dumps({'pi_version': version, 'gate_plus_product': True,
                                    'allow_runs': 1, 'deny_runs': 0, 'deny_error': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('Gate + 产品同开：allow 恰 1 次；deny 0 次且 error；无绕过')
