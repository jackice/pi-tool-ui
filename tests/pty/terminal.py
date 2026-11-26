import errno
import fcntl
import json
import os
import pty
import select
import struct
import subprocess
import termios
import time


def capture_tui(command, env, root, done, expected, key=None, after=None, rows=40, cols=100):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
    output = bytearray()
    try:
        with subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=root, env=env) as process:
            os.close(slave)
            try:
                deadline = time.monotonic() + 12
                while output.find(done) < 0 and time.monotonic() < deadline:
                    if select.select([master], [], [], 0.2)[0]:
                        try:
                            output.extend(os.read(master, 65536))
                        except OSError as exc:
                            if exc.errno == errno.EIO:
                                break
                            raise
                assert output.find(done) >= 0, output[-4000:].decode(errors='replace')
                deadline = time.monotonic() + 12
                while expected not in output and time.monotonic() < deadline:
                    if select.select([master], [], [], 0.2)[0]:
                        try:
                            output.extend(os.read(master, 65536))
                        except OSError as exc:
                            if exc.errno == errno.EIO:
                                break
                            raise
                assert expected in output, output[-4000:].decode(errors='replace')
                if key is not None and after is None:
                    os.write(master, key)
                    deadline = time.monotonic() + 0.9
                    while time.monotonic() < deadline:
                        if select.select([master], [], [], 0.1)[0]:
                            try:
                                output.extend(os.read(master, 65536))
                            except OSError as exc:
                                if exc.errno == errno.EIO:
                                    break
                                raise
                elif key is not None and after is not None:
                    start = len(output)
                    os.write(master, key)
                    deadline = time.monotonic() + 12
                    while output.find(after, start) < 0 and time.monotonic() < deadline:
                        if select.select([master], [], [], 0.2)[0]:
                            try:
                                output.extend(os.read(master, 65536))
                            except OSError as exc:
                                if exc.errno == errno.EIO:
                                    break
                                raise
                    assert output.find(after, start) >= 0, output[-4000:].decode(errors='replace')
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
    finally:
        os.close(master)
    return bytes(output)


def run_tui(command, env, root, expected_result, *, expand=False, reload=False, switch_theme=False, rows=40, cols=100):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
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
                assert expected_result in output, output[-4000:].decode(errors='replace')
                if reload:
                    start = len(output)
                    os.write(master, b'/reload\r')
                    receive(b'Reloaded keybindings, extensions', start)
                if switch_theme:
                    start = len(output)
                    os.write(master, b'/probe-light\r')
                    receive(b'PROBE_THEME_CHANGED', start)
                if not expand:
                    return bytes(output)
                assert b'PROBE_CALL' in output
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
    return bytes(output)


def export_tui(command, env, root, done, output_path, rows=40, cols=100):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
    output = bytearray()
    try:
        with subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=root, env=env) as process:
            os.close(slave)
            try:
                def wait_for(marker, start):
                    deadline = time.monotonic() + 15
                    while output.find(marker, start) < 0 and time.monotonic() < deadline:
                        if select.select([master], [], [], 0.2)[0]:
                            try:
                                output.extend(os.read(master, 65536))
                            except OSError as exc:
                                if exc.errno == errno.EIO:
                                    break
                                raise
                    assert output.find(marker, start) >= 0, output[-4000:].decode(errors='replace')

                wait_for(done, 0)
                os.write(master, f'/export {output_path}\r'.encode())
                wait_for(b'Session exported to:', len(output))
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
    finally:
        os.close(master)
    return bytes(output)
