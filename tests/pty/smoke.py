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


probe = Path(__file__).with_name('probe.ts').resolve()
pi = shutil.which('pi')
if pi is None:
    raise SystemExit('需要 Pi 1.6.0')
with tempfile.TemporaryDirectory(prefix='pi-tool-ui-') as directory:
    root = Path(directory)
    (root / 'fixture.txt').write_text('fixture from isolated cwd\n')
    env = dict(PATH=os.environ['PATH'], HOME=directory, TERM='xterm-256color',
               PI_CODING_AGENT_DIR=str(root / 'agent'), PI_TELEMETRY='0',
               PI_TOOL_UI_PROBE_LOG=str(root / 'events.jsonl'))
    command = [pi, '--offline', '--no-approve', '-ne', '-ns', '-np', '-nc', '--no-mcp',
               '--no-session', '-e', str(probe), '--model', 'tool-ui-probe/local',
               '--tools', 'read', 'Run the local fixture']
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
    output = bytearray()
    try:
        with subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=root, env=env) as process:
            os.close(slave)
            try:
                def receive(marker, start=0):
                    deadline = time.monotonic() + 12
                    while output.find(marker, start) < 0 and time.monotonic() < deadline:
                        if select.select([master], [], [], 0.2)[0]:
                            try:
                                output.extend(os.read(master, 65536))
                            except OSError as exc:
                                if exc.errno == errno.EIO:
                                    break
                                raise
                    assert output.find(marker, start) >= 0, output[-4000:].decode(errors='replace')

                receive(b'PROBE_DONE')
                assert b'PROBE_CALL' in output and b'PROBE_RESULT' in output
                before_expand = len(output)
                os.write(master, b'\x0f')
                receive(b'PROBE_RESULT', before_expand)
                events = [json.loads(line) for line in (root / 'events.jsonl').read_text().splitlines()]
                results = [item for item in events if item['event'] == 'result' and not item['partial']]
                assert any(item['shared'] and not item['error'] and 'fixture from isolated cwd' in item['content'][0]['text'] for item in results), events
                assert {item['expanded'] for item in results} == {False, True}, events
                assert any(item['reused'] for item in results), events
                print(json.dumps(events, ensure_ascii=False, indent=2))
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
    finally:
        os.close(master)
