import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from screen import render
from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/write-cases-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-write-ab-') as directory:
    root = Path(directory)
    observed = {}
    for enabled in (False, True):
        work = root / ('on' if enabled else 'off')
        work.mkdir()
        agent = work / 'agent'
        agent.mkdir()
        settings = {'packages': [str(repo)], 'toolUi': {'enabled': enabled, 'tools': {'write': {'enabled': enabled}}}}
        (agent / 'settings.json').write_text(json.dumps(settings))
        log = work / 'events.jsonl'
        env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
                   PI_CODING_AGENT_DIR=str(agent), PI_WRITE_CASE='success',
                   PI_TOOL_UI_PROBE_LOG=str(log), PI_TOOL_UI_PROBE_RENDER='0')
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                              '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'write',
                              '--session', str(work / 'session.jsonl'), 'Run the local write'], env, work, b'WRITE_DONE', b'WRITE_DONE', rows=60)
        events = [json.loads(line) for line in log.read_text().splitlines()]
        args = None
        result = []
        session = work / 'session.jsonl'
        if session.exists():
            for line in session.read_text().splitlines():
                entry = json.loads(line)
                message = entry.get('message')
                if entry.get('type') != 'message' or not isinstance(message, dict):
                    continue
                if message.get('role') == 'assistant':
                    for block in message.get('content', []):
                        if block.get('type') == 'toolCall' and block.get('name') == 'write':
                            args = block.get('arguments')
                if message.get('role') == 'toolResult':
                    result = [block.get('text', '') for block in message.get('content', []) if block.get('type') == 'text']
        observed['on' if enabled else 'off'] = {
            'bytes': (work / 'out.txt').read_text() if (work / 'out.txt').exists() else None,
            'executions': sum(1 for item in events if item.get('event') == 'tool-execution'),
            'args': args,
            'result': result,
            'text': '\n'.join(render(screen)),
        }

    assert observed['on']['bytes'] == observed['off']['bytes'] == 'alpha\nbeta\n'
    assert observed['on']['executions'] == observed['off']['executions'] == 1
    assert observed['on']['args'] == observed['off']['args']
    assert observed['on']['result'] == observed['off']['result']
    assert '╭─ Write' in observed['on']['text']
    assert '╭─ Write' not in observed['off']['text']
    evidence = repo / 'docs/evidence/write-product-ab.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'bytes_equal': True,
        'args_equal': True,
        'result_equal': True,
        'runs': 1,
        'card_on': True,
        'card_off': False,
    }, ensure_ascii=False, indent=2) + '\n')
    print('Write 产品 A/B：文件 bytes/args/result 一致，各执行 1 次，ON 有卡片、OFF 无')
