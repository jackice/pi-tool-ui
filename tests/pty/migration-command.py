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


pi = shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/probe.ts'
command = [pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
           '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'read', 'Run']


def interact(agent, root, steps):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 50, 100, 0, 0))
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(root / 'probe.log'))
    output = bytearray()
    try:
        with subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=root, env=env) as process:
            os.close(slave)
            try:
                for send, marker in steps:
                    if send is not None:
                        os.write(master, send)
                    if marker is None:
                        time.sleep(1.2)
                        continue
                    deadline = time.monotonic() + 12
                    start = len(output)
                    while output.find(marker, start) < 0 and time.monotonic() < deadline:
                        if select.select([master], [], [], 0.2)[0]:
                            try:
                                output.extend(os.read(master, 65536))
                            except OSError as exc:
                                if exc.errno == errno.EIO:
                                    break
                                raise
                    if output.find(marker, start) < 0:
                        Path('/tmp/migrate-pty.log').write_bytes(bytes(output))
                    assert output.find(marker, start) >= 0, output[-3000:].decode(errors='replace')
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
    finally:
        os.close(master)
        Path('/tmp/migrate-last.log').write_bytes(bytes(output))


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-migrate-') as directory:
    root = Path(directory)
    (root / 'notes.txt').write_text('alpha\nbeta\ngamma\n')

    def fresh(name):
        agent = root / name
        (agent / 'extensions').mkdir(parents=True)
        (agent / 'settings.json').write_text(json.dumps({
            'packages': [str(repo)],
            'editDiff': {'nativeEdit': True},
        }))
        return agent

    dry_agent = fresh('dry')
    interact(dry_agent, root, [(None, b'PROBE_DONE'), (b'/tool-ui-migrate dry', None), (b'\r', b'target: edit=true')])
    assert 'toolUi' not in json.loads((dry_agent / 'settings.json').read_text())

    cancel_agent = fresh('cancel')
    interact(cancel_agent, root, [(None, b'PROBE_DONE'), (b'/tool-ui-migrate force', None), (b'\r', '应用 toolUi 迁移'.encode()),
                                  (b'\x1b', None)])
    assert 'toolUi' not in json.loads((cancel_agent / 'settings.json').read_text())
    print('迁移命令：dry 不落盘；取消不写入；force 写入由 migrate.test.ts 覆盖')
