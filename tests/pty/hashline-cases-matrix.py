import json
import os
from pathlib import Path
import shutil
import tempfile

from screen import extract_card
from terminal import capture_tui


pi = shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
old = workspace / 'dotfiles/pi/.pi/agent/extensions/hashline-diff'
hashline = Path.home() / '.pi/agent/npm/node_modules/@jackice/hashline'
library = old / 'node_modules/@jackice/pi-ui'


def install_hashline(agent):
    shutil.copytree(hashline, agent / 'extensions/hashline')
    for native in ('pi-utils', 'pi-natives', 'pi-natives-darwin-arm64'):
        shutil.copytree(Path.home() / f'.pi/agent/npm/node_modules/@oh-my-pi/{native}',
                        agent / f'node_modules/@oh-my-pi/{native}')


def install_old(agent):
    shutil.copytree(old, agent / 'extensions/hashline-diff', ignore=shutil.ignore_patterns('node_modules'))
    (agent / 'extensions/hashline-diff/node_modules/@jackice').mkdir(parents=True)
    shutil.copytree(library, agent / 'extensions/hashline-diff/node_modules/@jackice/pi-ui')


def results(session):
    out = []
    for line in session.read_text().splitlines():
        entry = json.loads(line)
        message = entry.get('message', {})
        if entry.get('type') == 'message' and message.get('role') == 'toolResult':
            out.append([block.get('text', '') for block in message.get('content', [])])
    return out


def run_case(root, kind, files, provider, done):
    root.mkdir(parents=True, exist_ok=True)
    outcome = {}
    for name in ('old', 'new'):
        agent = root / f'{name}-agent'
        agent.mkdir()
        install_hashline(agent)
        if name == 'old':
            install_old(agent)
            settings = {'editDiff': {'nativeEdit': True}}
        else:
            settings = {'packages': [str(repo)], 'toolUi': {'enabled': True, 'tools': {'edit': {'enabled': True}, 'hashline': {'enabled': True}}}}
        (agent / 'settings.json').write_text(json.dumps(settings))
        work = root / name
        work.mkdir()
        for filename, content in files.items():
            (work / filename).write_text(content)
        session = work / 'session.jsonl'
        log = work / 'events.jsonl'
        env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color',
                   PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0', PI_TOOL_UI_PROBE_LOG=str(log))
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                              '-e', str(repo / 'tests/pty' / provider), '--model', 'tool-ui-probe/local',
                              '--tools', 'read,hashline', 'Run the local edit'], env, work, done.encode(), done.encode())
        outcome[name] = {
            'card': '\n'.join(extract_card(screen, work)),
            'results': results(session),
            'bytes': {filename: (work / filename).read_bytes() for filename in files},
            'executions': sum(1 for line in log.read_text().splitlines() if 'tool-execution' in line),
        }
    return outcome


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-hashline-cases-') as directory:
    base = Path(directory)
    noop = run_case(base / 'noop', 'noop', {'notes.txt': 'alpha\nbeta\ngamma\n'},
                    'hashline-noop-provider.ts', 'NOOP_DONE')
    assert noop['old']['results'] == noop['new']['results'], noop
    assert noop['old']['bytes'] == noop['new']['bytes']
    assert noop['old']['card'] == noop['new']['card'], noop
    assert noop['old']['executions'] == noop['new']['executions'] == 1, (noop['old']['executions'], noop['new']['executions'])

    multi = run_case(base / 'multi', 'multi', {'a.txt': 'alpha\n', 'b.txt': 'beta\n'},
                     'hashline-multifile-provider.ts', 'MULTI_DONE')
    assert multi['old']['results'] == multi['new']['results'], multi
    assert multi['old']['bytes'] == multi['new']['bytes']
    assert multi['old']['card'] == multi['new']['card'], multi
    assert multi['old']['executions'] == multi['new']['executions'] == 1, (multi['old']['executions'], multi['new']['executions'])

    evidence = repo / 'docs/evidence/hashline-cases.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({
        'noop': {'card_equal': True, 'results_equal': True, 'bytes_equal': True, 'executions': 1},
        'multifile': {'card_equal': True, 'results_equal': True, 'bytes_equal': True, 'executions': 1},
    }, ensure_ascii=False, indent=2) + '\n')
    print('noop 与多文件 Hashline：旧新卡片/结果/字节一致，各只执行一次')
