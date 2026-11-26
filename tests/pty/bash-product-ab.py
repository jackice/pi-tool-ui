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

from screen import extract_card, render


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
gate = workspace / 'pi-approval-gate'
compressor = workspace / 'dotfiles/pi/.pi/agent/extensions/pi-shell-compressor'
provider = repo / 'tests/pty/bash-cases-provider.ts'


def run(root, enabled):
    work = root / ('on' if enabled else 'off')
    work.mkdir(parents=True)
    agent = work / 'agent'
    (agent / 'extensions').mkdir(parents=True)
    shutil.copytree(gate, agent / 'extensions/approval-gate')
    shutil.copytree(compressor, agent / 'extensions/pi-shell-compressor')
    (work / '.pi/agent').mkdir(parents=True)
    shutil.copyfile(compressor / 'shell-compressor.json', work / '.pi/agent/shell-compressor.json')
    settings = {}
    if enabled:
        settings = {'packages': [str(repo)], 'toolUi': {'enabled': True, 'tools': {'bash': {'enabled': True}}}}
    (agent / 'settings.json').write_text(json.dumps(settings))
    log = work / 'events.jsonl'
    session = work / 'session.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE='count_compress',
               PI_TOOL_UI_PROBE_LOG=str(log), PI_TOOL_UI_PROBE_RENDER='0' if enabled else 'log')
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
    output = bytearray()
    command = [pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
               '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash',
               '--approval-timeout-ms', '9000', '--approval-arm-ms', '100', 'Run the local bash']
    try:
        with subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=work, env=env) as process:
            os.close(slave)
            try:
                def wait_for(marker):
                    deadline = time.monotonic() + 20
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
    compressor_details = None
    command = None
    result_text = None
    if session.exists():
        for line in session.read_text().splitlines():
            entry = json.loads(line)
            message = entry.get('message')
            if entry.get('type') != 'message' or not isinstance(message, dict):
                continue
            if message.get('role') == 'assistant':
                for block in message.get('content', []):
                    if block.get('type') == 'toolCall' and block.get('name') == 'bash':
                        command = (block.get('arguments') or {}).get('command')
            if message.get('role') == 'toolResult':
                compressor_details = (message.get('details') or {}).get('shellCompressor') or compressor_details
                result_text = '\n'.join(block.get('text', '') for block in message.get('content', []) if block.get('type') == 'text')
    count = work / 'count.txt'
    card = ''
    try:
        card = '\n'.join(extract_card(bytes(output), work))
    except ValueError:
        card = ''
    return {
        'runs': len(count.read_text().splitlines()) if count.exists() else 0,
        'model_text': model['text'],
        'compressor': compressor_details,
        'card': card,
        'text': '\n'.join(render(bytes(output))),
        'command': command,
        'result_text': result_text,
        'cwd': str(work),
    }


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-product-') as directory:
    root = Path(directory)
    on = run(root, True)
    off = run(root, False)
    assert on['runs'] == off['runs'] == 1, (on['runs'], off['runs'])
    assert on['model_text'] == off['model_text'] and on['model_text'].startswith('# shell-compressor')
    assert on['compressor'] and on['compressor']['originalChars'] > on['compressor']['compressedChars'] > 0, on['compressor']
    assert on['card'] and 'Bash' in on['card'], on['card'][:200]
    assert '╭─ Bash' not in off['text'], off['text'][-300:]
    assert on['command'] == off['command'] == 'echo run >> count.txt; for i in $(seq 1 100); do echo same-line; done'
    assert on['result_text'] == off['result_text']
    assert on['cwd'] != off['cwd']
    assert on['text'].count('echo run >> count.txt') == 1, on['text'][-300:]
    evidence = repo / 'docs/evidence/bash-product-ab.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'runs_on': on['runs'],
        'runs_off': off['runs'],
        'model_text_equal': True,
        'compressor': on['compressor'],
        'card_on': True,
        'card_off': False,
        'command_equal': True,
        'result_text_equal': True,
        'cwd_recorded': [on['cwd'], off['cwd']],
        'command_once': True,
    }, ensure_ascii=False, indent=2) + '\n')
    print('Bash 产品 A/B：Gate+Compressor 下各执行 1 次，模型结果一致，ON 有 Bash 卡片、OFF 无')
