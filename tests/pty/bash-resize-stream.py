import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import tempfile
import termios
import time

import pyte

from terminal import capture_tui


pi = os.environ.get('PI_BIN') or __import__('shutil').which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/bash-cases-provider.ts'


def feed(data, columns):
    screen = pyte.Screen(columns, 60)
    pyte.Stream(screen).feed(data.decode(errors='replace'))
    return [line.rstrip() for line in screen.display]


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-resize-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'bash': {'enabled': True}}},
    }))
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(root / 'events.jsonl'),
               PI_TOOL_UI_PROBE_RENDER='0')

    def run(case, marker, resize=None, cols=100, rows=60):
        env_case = dict(env, PI_BASH_CASE=case)
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
        output = bytearray()
        try:
            with subprocess.Popen([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                                   '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash',
                                   'Run the local bash'], stdin=slave, stdout=slave, stderr=slave,
                                  cwd=root, env=env_case) as process:
                os.close(slave)
                try:
                    deadline = time.monotonic() + 15
                    while output.find(marker) < 0 and time.monotonic() < deadline:
                        if select.select([master], [], [], 0.1)[0]:
                            try:
                                output.extend(os.read(master, 65536))
                            except OSError as exc:
                                if exc.errno == errno.EIO:
                                    break
                                raise
                    assert output.find(marker) >= 0, output[-2000:].decode(errors='replace')
                    if resize is not None:
                        resize_start = len(output)
                        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', rows, resize, 0, 0))
                        time.sleep(0.4)
                        os.write(master, b'\x0f')
                        time.sleep(0.3)
                        os.write(master, b'\x0f')
                        deadline = time.monotonic() + 5
                        while b'Bash' not in output[resize_start:] and time.monotonic() < deadline:
                            if select.select([master], [], [], 0.1)[0]:
                                try:
                                    output.extend(os.read(master, 65536))
                                except OSError:
                                    break
                        while select.select([master], [], [], 0.1)[0]:
                            try:
                                output.extend(os.read(master, 65536))
                            except OSError:
                                break
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
        finally:
            os.close(master)
        result = bytes(output)
        return (result, resize_start if resize is not None else 0)

    resize_output, resize_start = run('success', b'BASH_DONE', resize=60)
    assert ("─" * 60).encode() in resize_output[resize_start:], resize_output[resize_start:][-400:]

    narrow_output = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                                 '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash',
                                 'Run the local bash'], dict(env, PI_BASH_CASE='success'), root,
                                b'BASH_DONE', b'BASH_DONE', rows=60, cols=60)
    narrow = feed(narrow_output, 60)
    borders = [line.lstrip() for line in narrow if 'Bash' in line and '╭' in line]
    assert borders and borders[-1].startswith('╭') and borders[-1].endswith('╮') and len(borders[-1]) <= 60, borders[-3:]

    stream_output, _ = run('stream', '●'.encode())
    stream_lines = feed(stream_output, 100)
    assert any('Bash' in line and '●' in line and '✓' not in line for line in stream_lines), stream_lines[-20:]

    evidence = repo / 'docs/evidence/bash-resize-stream.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'resize_100_to_60': True,
        'stream_running_frame': True,
    }, ensure_ascii=False, indent=2) + '\n')
    print('Bash resize 100→60 重绘无溢出；流式帧显示 running 状态')
