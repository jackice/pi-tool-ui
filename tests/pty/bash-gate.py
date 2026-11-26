import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shutil
import stat
import struct
import subprocess
import tempfile
import termios
import time


pi = shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
gate = workspace / 'pi-approval-gate'
provider = repo / 'tests/pty/bash-cases-provider.ts'


def interact(root, agent, env, marker, approve):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
    command = [pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
               '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash',
               '--approval-timeout-ms', '900', '--approval-arm-ms', '100', 'Run the local bash']
    output = bytearray()
    try:
        with subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=root, env=env) as process:
            os.close(slave)
            try:
                deadline = time.monotonic() + 15
                while output.find(marker) < 0 and time.monotonic() < deadline:
                    if select.select([master], [], [], 0.2)[0]:
                        try:
                            output.extend(os.read(master, 65536))
                        except OSError as exc:
                            if exc.errno == errno.EIO:
                                break
                            raise
                assert output.find(marker) >= 0, output[-3000:].decode(errors='replace')
                if approve:
                    time.sleep(0.4)
                    os.write(master, b'\r')
                deadline = time.monotonic() + 15
                while output.find(b'BASH_DONE') < 0 and time.monotonic() < deadline:
                    if select.select([master], [], [], 0.2)[0]:
                        try:
                            output.extend(os.read(master, 65536))
                        except OSError as exc:
                            if exc.errno == errno.EIO:
                                break
                            raise
                assert output.find(b'BASH_DONE') >= 0, output[-3000:].decode(errors='replace')
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
    finally:
        os.close(master)


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-gate-') as directory:
    root = Path(directory)
    secret = root / 'secret.txt'
    secret.write_text('secret\n')
    secret.chmod(0o644)
    base_env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0')
    observed = {}
    for name, approve, timeout in (('allow', True, '900'), ('deny', False, '900')):
        work = root / name
        work.mkdir()
        shutil.copyfile(secret, work / 'secret.txt')
        (work / 'secret.txt').chmod(0o644)
        agent = work / 'agent'
        (agent / 'extensions').mkdir(parents=True)
        shutil.copytree(gate, agent / 'extensions/approval-gate')
        (agent / 'settings.json').write_text('{}')
        log = work / 'events.jsonl'
        env = dict(base_env, PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE='risky', PI_TOOL_UI_PROBE_LOG=str(log))
        interact(work, agent, env, b'navigate', approve)
        events = [json.loads(line) for line in log.read_text().splitlines()]
        final = next(item for item in events if not item['partial'])
        observed[name] = {
            'error': final['error'],
            'text': [block.get('text', '') for block in final['content']],
            'mode': stat.S_IMODE((work / 'secret.txt').stat().st_mode),
        }

    assert observed['allow']['error'] is False and observed['allow']['mode'] == 0o000, observed
    assert observed['deny']['error'] is True and observed['deny']['mode'] == 0o644, observed
    assert 'Blocked by approval gate' in observed['deny']['text'][0]
    evidence = repo / 'docs/evidence/bash-gate.json'
    evidence.write_text(json.dumps(observed, ensure_ascii=False, indent=2) + '\n')
    print('Approval Gate：允许执行 chmod（模式 000），拒绝块返回 error 且模式保持 644')
