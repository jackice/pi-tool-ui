import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import re
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


def run_tui(command, env, root, expected_result, *, expand=False, reload=False, done=b'PROBE_DONE'):
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

                receive(done)
                assert expected_result in output, output[-4000:].decode(errors='replace')
                if reload:
                    start = len(output)
                    os.write(master, b'/reload\r')
                    receive(b'Reloaded keybindings, extensions', start)
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


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-') as directory:
    root = Path(directory)
    (root / 'fixture.txt').write_text('fixture from isolated cwd\n')
    log = root / 'events.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=directory, TERM='xterm-256color',
               PI_CODING_AGENT_DIR=str(root / 'agent'), PI_TELEMETRY='0',
               PI_TOOL_UI_PROBE_LOG=str(log))
    base = [pi, '--offline', '--no-approve', '-ne', '-ns', '-np', '-nc', '--no-mcp', '--no-session']
    tail = ['--model', 'tool-ui-probe/local', '--tools', 'read', 'Run the local fixture']
    command = [*base, '-e', str(probe), *tail]
    run_tui(command, env, root, b'PROBE_RESULT', expand=True)

    peer = probe.with_name('peer.ts')
    for order, entered, passthrough, shown in [
        ((probe, peer), ['probe-enter', 'peer-enter'], False, b'PROBE_RESULT'),
        ((peer, probe), ['peer-enter', 'probe-enter'], False, b'PEER_RESULT'),
        ((probe, peer), ['probe-enter', 'peer-enter'], True, b'PEER_RESULT'),
    ]:
        log.unlink()
        scenario = [*base, '-e', str(order[0]), '-e', str(order[1]), *tail]
        screen = run_tui(scenario, dict(env, PI_TOOL_UI_PROBE_PASS=str(int(passthrough))), root, shown)
        assert (b'PEER_RESULT' in screen) != (b'PROBE_RESULT' in screen)
        events = [json.loads(line) for line in log.read_text().splitlines()]
        assert [item['event'] for item in events if item['event'].endswith('-enter')] == entered, events
        assert sum(item['event'] == 'resolve' for item in events) == 1, events
        assert sum(item['event'] == 'peer-return' for item in events) == 1, events
        print(' → '.join(entered), 'pass=' + str(passthrough), shown.decode())

    (root / 'events.jsonl').unlink()
    printed = subprocess.run([*command[:-1], '--print', command[-1]], cwd=root, env=env,
                             capture_output=True, text=True, timeout=12, check=True)
    assert 'PROBE_DONE' in printed.stdout, printed.stdout + printed.stderr
    headless = [json.loads(line) for line in (root / 'events.jsonl').read_text().splitlines()]
    assert headless == [{'event': 'session', 'hasUI': False}, {'event': 'tool-execution'}], headless
    print('无 UI：原生 read 到达最终回复，未调用 renderer')

    log.unlink()
    session = root / 'history.jsonl'
    saved = [*base[:-1], '--session', str(session), '-e', str(probe), *tail]
    subprocess.run([*saved[:-1], '--print', saved[-1]], cwd=root, env=env,
                   capture_output=True, text=True, timeout=12, check=True)
    assert session.is_file(), 'Pi 未生成历史会话'
    (root / 'fixture.txt').write_text('changed after original execution\n')
    log.unlink()
    run_tui(saved[:-1], env, root, b'PROBE_RESULT', reload=True)
    assert b'PROBE_DONE' in session.read_bytes()
    replay = [json.loads(line) for line in log.read_text().splitlines()]
    results = [item for item in replay if item['event'] == 'result']
    assert results and all(item['content'] == [{'type': 'text', 'text': 'fixture from isolated cwd\n'}]
                           and not item['partial'] for item in results), replay
    assert results[0]['shared'] and not results[0]['reused'], replay
    assert not any(item['event'] == 'tool-execution' for item in replay), replay
    assert sum(item['event'] == 'session' for item in replay) == 2, replay
    assert sum(not item['reused'] for item in results) >= 2, replay
    print('历史回放：使用保存的 final，未重跑 Read')

    peer_command = [*base, '-e', str(probe), '-e', str(peer), *tail]
    log.unlink()
    screen = run_tui(peer_command, dict(env, PI_TOOL_UI_PROBE_FAIL='1'), root, b'PEER_RESULT')
    assert b'PROBE_RESULT' not in screen
    failure = [json.loads(line) for line in log.read_text().splitlines()]
    assert sum(item['event'] == 'fallback' for item in failure) == 1, failure
    assert sum(item['event'] == 'tool-execution' for item in failure) == 1, failure

    theme_rows = []
    for theme in ('dark', 'light'):
        log.unlink()
        run_tui([*command[:-1], '--use-theme', theme, command[-1]], env, root, b'PROBE_RESULT')
        events = [json.loads(line) for line in log.read_text().splitlines()]
        entry = next(item for item in events if item['event'] == 'highlight')
        assert entry['language'] in ('ts', 'typescript'), entry
        assert [re.sub(r'\x1b\[[0-9;]*m', '', line) for line in entry['rows']] == ['const value = 42;'], entry
        assert any('\x1b[' in line for line in entry['rows']), entry
        theme_rows.append(entry['rows'])
    assert theme_rows[0] != theme_rows[1], theme_rows
    print('主题与高亮：dark/light 均保留源码，样式不同；故障回退保留自定义下游')
