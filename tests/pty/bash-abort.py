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
abort_extension = repo / 'tests/pty/bash-abort-extension.ts'


def interact(root, agent, case, abort_ms, approve):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE=case,
               PI_ABORT_AFTER_MS=str(abort_ms), PI_TOOL_UI_PROBE_LOG=str(root / 'events.jsonl'))
    command = [pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
               '-e', str(provider), '-e', str(abort_extension), '--model', 'tool-ui-probe/local',
               '--tools', 'bash', '--approval-timeout-ms', '9000', '--approval-arm-ms', '100',
               'Run the local bash']
    output = bytearray()

    def wait_for(marker, start=0):
        deadline = time.monotonic() + 20
        while output.find(marker, start) < 0 and time.monotonic() < deadline:
            if select.select([master], [], [], 0.2)[0]:
                try:
                    output.extend(os.read(master, 65536))
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
        assert output.find(marker, start) >= 0, output[-2500:].decode(errors='replace')

    try:
        with subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=root, env=env) as process:
            os.close(slave)
            try:
                wait_for(b'navigate')
                if approve:
                    time.sleep(0.3)
                    os.write(master, b'\r')
                wait_for(b'Operation aborted')
                if case == 'risky_abort':
                    time.sleep(5.5)
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
    finally:
        os.close(master)
    events = [json.loads(line) for line in (root / 'events.jsonl').read_text().splitlines()] if (root / 'events.jsonl').exists() else []
    finals = [item for item in events if item.get('event') == 'result' and not item['partial']]
    if finals:
        text = '\n'.join(block.get('text', '') for block in finals[-1]['content'] if block.get('type') == 'text')
        error = finals[-1]['error']
    else:
        text = bytes(output)[-2000:].decode(errors='replace')
        error = True
    count = root / 'count.txt'
    return {
        'error': error,
        'runs': len(count.read_text().splitlines()) if count.exists() else 0,
        'text_tail': text[-300:],
    }


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-abort-') as directory:
    root = Path(directory)
    observed = {}
    for name, case, abort_ms, approve in (('approval', 'risky_slow', 300, False), ('execution', 'risky_abort', 1500, True)):
        work = root / name
        work.mkdir()
        agent = work / 'agent'
        (agent / 'extensions').mkdir(parents=True)
        shutil.copytree(gate, agent / 'extensions/approval-gate')
        (agent / 'settings.json').write_text('{}')
        observed[name] = interact(work, agent, case, abort_ms, approve)

    for name, value in observed.items():
        assert value['error'] is True and value['runs'] == 0, (name, value)
        assert 'abort' in value['text_tail'].lower() or 'cancel' in value['text_tail'].lower(), (name, value)
    assert 'aborted' in observed['execution']['text_tail'].lower() or 'abort' in observed['execution']['text_tail'].lower()
    assert 'Full output:' in observed['execution']['text_tail'] or 'Showing lines' in observed['execution']['text_tail']
    evidence = repo / 'docs/evidence/bash-abort.json'
    evidence.write_text(json.dumps({'pi_version': version, **observed}, ensure_ascii=False, indent=2) + '\n')
    print('Bash AbortSignal：审批中与执行中取消均 error、计数 0、无迟到副作用')
