import errno
import fcntl
import hashlib
import json
import os
import pty
import select
import struct
import termios
import time
from pathlib import Path
import shutil
import subprocess
import tempfile

from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
gate = workspace / 'pi-approval-gate'
compressor = workspace / 'dotfiles/pi/.pi/agent/extensions/pi-shell-compressor'
provider = repo / 'tests/pty/bash-cases-provider.ts'


def run(root, render):
    work = root / ('on' if render else 'off')
    work.mkdir(parents=True)
    agent = work / 'agent'
    (agent / 'extensions').mkdir(parents=True)
    (agent / 'settings.json').write_text('{}')
    shutil.copytree(gate, agent / 'extensions/approval-gate')
    shutil.copytree(compressor, agent / 'extensions/pi-shell-compressor')
    (work / '.pi/agent').mkdir(parents=True)
    shutil.copyfile(compressor / 'shell-compressor.json', work / '.pi/agent/shell-compressor.json')
    log = work / 'events.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE='count',
               PI_TOOL_UI_PROBE_LOG=str(log), PI_TOOL_UI_PROBE_RENDER='1' if render else '0')
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
    output = bytearray()
    command = [pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
               '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash',
               '--approval-timeout-ms', '9000', '--approval-arm-ms', '100', 'Run the local bash']
    try:
        with subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=work, env=env) as process:
            os.close(slave)
            try:
                def wait_for(marker):
                    deadline = time.monotonic() + 15
                    start = len(output)
                    while output.find(marker, start) < 0 and time.monotonic() < deadline:
                        if select.select([master], [], [], 0.2)[0]:
                            try:
                                output.extend(os.read(master, 65536))
                            except OSError as exc:
                                if exc.errno == errno.EIO:
                                    break
                                raise
                    assert output.find(marker, start) >= 0, output[-3000:].decode(errors='replace')
                wait_for(b'navigate')
                time.sleep(0.3)
                os.write(master, b'\r')
                wait_for(b'BASH_DONE')
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
    finally:
        os.close(master)
    events = [json.loads(line) for line in log.read_text().splitlines()]
    model = next(item for item in events if item.get('event') == 'model')
    count = work / 'count.txt'
    return {
        'runs': len(count.read_text().splitlines()) if count.exists() else 0,
        'model_text': model['text'],
    }


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-renderer-') as directory:
    root = Path(directory)
    on = run(root, True)
    off = run(root, False)
    assert on['runs'] == off['runs'] == 1, (on['runs'], off['runs'])
    assert on['model_text'] == off['model_text'], (on['model_text'], off['model_text'])
    evidence = repo / 'docs/evidence/bash-renderer-ab.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'runs_on': on['runs'],
        'runs_off': off['runs'],
        'model_text_equal': True,
        'model_text': on['model_text'][:200],
        'stack': 'approval-gate + shell-compressor',
    }, ensure_ascii=False, indent=2) + '\n')
    print('Bash renderer OFF/ON：Gate+Compressor 栈下各执行 1 次，模型结果逐字一致')
