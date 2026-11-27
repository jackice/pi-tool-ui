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

from screen import render


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'


def run(work, enabled):
    agent = work / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)] if enabled else [],
        'toolUi': {'enabled': enabled, 'tools': {'bash': {'enabled': enabled}}},
    }))
    env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent))
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
    output = bytearray()
    try:
        with subprocess.Popen([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                               '--tools', 'bash'], stdin=slave, stdout=slave, stderr=slave,
                              cwd=work, env=env) as process:
            os.close(slave)
            try:
                deadline = time.monotonic() + 12
                while b'commands' not in output and time.monotonic() < deadline:
                    if select.select([master], [], [], 0.2)[0]:
                        output.extend(os.read(master, 65536))
                assert b'commands' in output, output[-2000:].decode(errors='replace')
                os.write(master, b"!printf 'USER_BASH_OK\\n' >> user-bash.txt\r")
                deadline = time.monotonic() + 12
                while b'USER_BASH_OK' not in output and time.monotonic() < deadline:
                    if select.select([master], [], [], 0.2)[0]:
                        try:
                            output.extend(os.read(master, 65536))
                        except OSError as exc:
                            if exc.errno == errno.EIO:
                                break
                            raise
                time.sleep(0.3)
                os.write(master, b"!!printf 'SILENT_OK\\n' >> user-bash.txt\r")
                time.sleep(0.6)
                while select.select([master], [], [], 0)[0]:
                    output.extend(os.read(master, 65536))
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
    finally:
        os.close(master)
    return {
        'screen': '\n'.join(render(bytes(output), lines=40)),
        'file': (work / 'user-bash.txt').read_text() if (work / 'user-bash.txt').exists() else None,
    }


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-userbash-') as directory:
    root = Path(directory)
    on = run(root / 'on', True) if (root / 'on').mkdir() is None else None
    off = run(root / 'off', False) if (root / 'off').mkdir() is None else None
    for name, result in (('on', on), ('off', off)):
        assert result['file'] == 'USER_BASH_OK\nSILENT_OK\n', (name, result)
        assert 'USER_BASH_OK' in result['screen'], (name, result['screen'][-1000:])
        assert '╭─ Bash' not in result['screen'], (name, result['screen'][-1000:])
    evidence = repo / 'docs/evidence/user-bash.json'
    evidence.write_text(json.dumps({'pi_version': version, 'user_bash_runs': 1, 'silent_bang_bang': True,
                                    'product_card': False, 'on_off_equal': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('用户 ! Bash：ON/OFF 各执行一次；输出保留；产品不渲染工具卡片')
