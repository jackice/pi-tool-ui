import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from screen import extract_card, render
from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/integration-provider.ts'


def read_results(session):
    results = []
    for line in session.read_text().splitlines():
        entry = json.loads(line)
        message = entry.get('message')
        if entry.get('type') == 'message' and isinstance(message, dict) and message.get('role') == 'toolResult':
            results.append({'content': message.get('content'), 'details': message.get('details')})
    return results


def normalise(value, root):
    return json.loads(json.dumps(value).replace(str(root), '<ROOT>'))


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-integration-') as directory:
    root = Path(directory)
    observed = {}
    for enabled in (False, True):
        work = root / ('on' if enabled else 'off')
        work.mkdir()
        agent = work / 'agent'
        agent.mkdir()
        settings = {'packages': [str(repo)] if enabled else [], 'toolUi': {'enabled': enabled, 'tools': {
            'bash': {'enabled': enabled}, 'write': {'enabled': enabled}, 'read': {'enabled': enabled}, 'edit': {'enabled': enabled},
        }}}
        (agent / 'settings.json').write_text(json.dumps(settings))
        log = work / 'events.jsonl'
        session = work / 'session.jsonl'
        env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
                   PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(log))
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                              '-e', str(provider), '--model', 'tool-ui-probe/local',
                              '--tools', 'write,read,bash', 'Run the local integration'],
                             env, work, b'INTEGRATION_DONE', b'INTEGRATION_DONE', rows=60)
        events = [json.loads(line) for line in log.read_text().splitlines()]
        results = read_results(session)
        observed['on' if enabled else 'off'] = {
            'results': [normalise(item, work) for item in results],
            'executions': {tool: sum(1 for item in events if item.get('tool') == tool) for tool in ('write', 'read', 'bash')},
            'files': {path.name: path.read_text() for path in work.iterdir() if path.suffix == '.txt'},
            'text': '\n'.join(render(screen, lines=60)),
        }

    assert observed['on']['results'] == observed['off']['results']
    assert observed['on']['executions'] == observed['off']['executions'] == {'write': 1, 'read': 1, 'bash': 1}
    assert observed['on']['files'] == observed['off']['files'] == {'out.txt': 'alpha\nbeta\n'}
    for card in ('╭─ Bash', '╭─ Write', '╭─ Read'):
        assert card in observed['on']['text'], (card, observed['on']['text'][-1200:])
        assert card not in observed['off']['text'], (card, observed['off']['text'][-1200:])

    log = root / 'on' / 'reload.log'
    session = root / 'on' / 'session.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root / 'on'), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(root / 'on' / 'agent'), PI_TOOL_UI_PROBE_LOG=str(log))
    reload_screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                                 '-e', str(provider), '--model', 'tool-ui-probe/local',
                                 '--tools', 'write,read,bash'],
                                env, root / 'on', b'INTEGRATION_DONE', b'INTEGRATION_DONE',
                                key=b'/reload\r', after=b'Reloaded keybindings, extensions', rows=60)
    reload_events = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    assert not any(item.get('event') == 'execute' for item in reload_events), reload_events
    assert b'Failed to load extension' not in reload_screen, reload_screen[-2000:]
    evidence = repo / 'docs/evidence/integration-matrix.json'
    evidence.write_text(json.dumps({'pi_version': version, 'tools': ['bash', 'write', 'read'],
                                    'results_equal': True, 'executions': {'write': 1, 'read': 1, 'bash': 1},
                                    'files_equal': True, 'cards_on': True, 'cards_off': False,
                                    'reload_re_executed': False},
                                   ensure_ascii=False, indent=2) + '\n')
    print('集成矩阵：Bash/Write/Read OFF/ON content/details/files 一致各执行一次；卡片互斥；/reload 不重跑')
