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
gate = workspace / 'pi-approval-gate'
provider = repo / 'tests/pty/bash-cases-provider.ts'


def run(work, agent, action, *, guard=False):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
    env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE='guard_pip' if guard else ('risky_slow' if action == 'cancel' else 'risky'),
               PI_BASH_TIMEOUT='1' if action == 'cancel' else '0',
               PI_TOOL_UI_PROBE_LOG=str(work / 'events.jsonl'), PI_TOOL_UI_PROBE_RENDER='log')
    command = [pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
               '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash',
               '--approval-timeout-ms', '900', '--approval-arm-ms', '100', 'Run the local bash']
    output = bytearray()
    count = work / 'count.txt'

    def wait_for(marker, start=0):
        deadline = time.monotonic() + 15
        while output.find(marker, start) < 0 and time.monotonic() < deadline:
            if select.select([master], [], [], 0.2)[0]:
                try:
                    output.extend(os.read(master, 65536))
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
        assert output.find(marker, start) >= 0, output[-3000:].decode(errors='replace')

    try:
        with subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, cwd=work, env=env) as process:
            os.close(slave)
            try:
                if not guard:
                    wait_for(b'navigate')
                    assert not count.exists(), '批准前命令已执行'
                    time.sleep(0.2)
                    if action == 'allow':
                        os.write(master, b'\r')
                    elif action == 'deny':
                        os.write(master, b'\x1b')
                    elif action == 'cancel':
                        os.write(master, b'\r')
                wait_for(b'BASH_DONE')
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
    finally:
        os.close(master)
    events = [json.loads(line) for line in (work / 'events.jsonl').read_text().splitlines()]
    final = next(item for item in events if item.get('event') == 'result' and not item['partial'])
    return {
        'runs': len(count.read_text().splitlines()) if count.exists() else 0,
        'error': final['error'],
        'text': [block.get('text', '') for block in final['content']],
        'screen': '\n'.join(render(bytes(output), lines=50)),
    }


def agent_for(work, guard=None):
    agent = work / 'agent'
    (agent / 'extensions').mkdir(parents=True)
    shutil.copytree(gate, agent / 'extensions/approval-gate')
    settings = {'packages': [str(repo)], 'toolUi': {'enabled': True, 'tools': {'bash': {'enabled': True}}}}
    if guard is not None:
        settings['approvalGate'] = {'guard': guard}
    (agent / 'settings.json').write_text(json.dumps(settings))
    return agent


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-secstack-') as directory:
    root = Path(directory)
    observed = {}
    for action in ('allow', 'deny', 'timeout', 'cancel'):
        work = root / action
        work.mkdir()
        observed[action] = run(work, agent_for(work), action)

    assert observed['allow']['runs'] == 1 and observed['allow']['error'] is False
    assert '╭─ Bash' in observed['allow']['screen'] and '✓' in observed['allow']['screen']
    assert '✗' not in observed['allow']['screen']

    for action in ('deny', 'timeout', 'cancel'):
        entry = observed[action]
        assert entry['runs'] == 0 and entry['error'] is True, action
        assert '╭─ Bash' in entry['screen'] and '✗' in entry['screen'], entry['screen'][-800:]
        assert '✓' not in entry['screen'], entry['screen'][-800:]
    assert 'Blocked by approval gate' in observed['deny']['text'][0]
    assert 'Blocked by approval gate' in observed['timeout']['text'][0]
    assert 'Command timed out' in observed['cancel']['text'][0]

    guard_results = {}
    for enabled in (False, True):
        work = root / f'guard-{"on" if enabled else "off"}'
        work.mkdir()
        agent = work / 'agent'
        (agent / 'extensions').mkdir(parents=True)
        settings = {'packages': [str(repo)] if enabled else [],
                    'toolUi': {'enabled': enabled, 'tools': {'bash': {'enabled': enabled}}},
                    'approvalGate': {'guard': 'uv'}}
        (agent / 'settings.json').write_text(json.dumps(settings))
        if not enabled:
            # Gate 仍需加载以提供 guard；产品关闭。
            shutil.copytree(gate, agent / 'extensions/approval-gate')
        else:
            shutil.copytree(gate, agent / 'extensions/approval-gate')
        guard_results['on' if enabled else 'off'] = run(work, agent, 'guard', guard=True)
    for enabled in (False, True):
        entry = guard_results['on' if enabled else 'off']
        assert entry['runs'] == 0 and entry['error'] is True
        assert 'pip is disabled' in entry['text'][0]
        if enabled:
            assert '╭─ Bash' in entry['screen'] and '✗' in entry['screen'], entry['screen'][-1200:]
        else:
            assert '╭─ Bash' not in entry['screen'], entry['screen'][-1200:]

    evidence = repo / 'docs/evidence/security-stack.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'gate_plus_product': True,
        'allow_runs': 1,
        'deny_runs': 0,
        'timeout_runs': 0,
        'exec_timeout_runs': 0,
        'cards_verified': True,
        'product_on_guard_blocked': guard_results['on']['runs'] == 0,
        'product_off_guard_blocked': guard_results['off']['runs'] == 0,
        'uv_guard_message': 'pip is disabled',
    }, ensure_ascii=False, indent=2) + '\n')
    print('Gate/uv + 产品：allow ✓ 1 次；deny/timeout/cancel ✗ 0 次；uv guard ON/OFF 均 0 次')
