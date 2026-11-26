import errno
import fcntl
import json
import os
import subprocess
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
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
gate = workspace / 'pi-approval-gate'
provider = repo / 'tests/pty/bash-cases-provider.ts'


def interact(work, agent, case, action, timeout_ms=0):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
    env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE=case,
               PI_BASH_TIMEOUT=str(timeout_ms),
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
                if action == 'allow':
                    time.sleep(0.2)
                    os.write(master, b'\r')
                elif action == 'esc':
                    time.sleep(0.2)
                    os.write(master, b'\x1b')
                elif action == 'cancel':
                    time.sleep(0.2)
                    os.write(master, b'\r')
                wait_for(b'BASH_DONE')
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
    finally:
        os.close(master)
    lines = count.read_text().splitlines() if count.exists() else []
    events = [json.loads(line) for line in (work / 'events.jsonl').read_text().splitlines()]
    final = next(item for item in events if item.get('event') == 'result' and not item['partial'])
    return {
        'runs': len(lines),
        'error': final['error'],
        'text': [block.get('text', '') for block in final['content']],
    }


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-gate-') as directory:
    root = Path(directory)
    observed = {}
    for name, case, action in (
        ('allow', 'risky', 'allow'),
        ('deny', 'risky', 'esc'),
        ('timeout', 'risky', 'timeout'),
        ('cancel', 'risky_slow', 'cancel'),
    ):
        work = root / name
        work.mkdir()
        agent = work / 'agent'
        (agent / 'extensions').mkdir(parents=True)
        shutil.copytree(gate, agent / 'extensions/approval-gate')
        (agent / 'settings.json').write_text('{}')
        observed[name] = interact(work, agent, case, action, 1 if name == 'cancel' else 0)

    assert observed['allow']['runs'] == 1 and observed['allow']['error'] is False, observed
    for name in ('deny', 'timeout', 'cancel'):
        assert observed[name]['runs'] == 0 and observed[name]['error'] is True, observed
    assert 'Blocked by approval gate' in observed['deny']['text'][0]
    assert 'Blocked by approval gate' in observed['timeout']['text'][0]
    evidence = repo / 'docs/evidence/bash-gate.json'
    observed['pi_version'] = version
    evidence.write_text(json.dumps(observed, ensure_ascii=False, indent=2) + '\n')
    print('Approval Gate：allow 恰执行 1 次；Esc 拒绝、超时、执行取消均为 0 且 error')
