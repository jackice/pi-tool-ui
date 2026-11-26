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
live = Path.home() / '.pi/agent'
installed = live / 'npm/node_modules'
provider = repo / 'tests/pty/edit-provider.ts'


def results(session):
    out = []
    for line in session.read_text().splitlines():
        entry = json.loads(line)
        message = entry.get('message', {})
        if entry.get('type') == 'message' and message.get('role') == 'toolResult':
            out.append([block.get('text', '') for block in message.get('content', [])])
    return out


def stack(root, name, with_old, link_package):
    agent = root / f'{name}-agent'
    shutil.copytree(workspace / 'dotfiles/pi/.pi/agent/extensions', agent / 'extensions')
    if not with_old:
        shutil.rmtree(agent / 'extensions/hashline-diff')
    for config in ('pi-prompt.json', 'shell-compressor.json', 'keybindings.json'):
        shutil.copyfile(live / config, agent / config)
    packages = []
    for spec in json.loads((live / 'settings.json').read_text())['packages']:
        package_name = spec.removeprefix('npm:')
        if '@' in package_name[1:]:
            package_name = package_name[:package_name.rindex('@')]
        target = installed / package_name
        assert (target / 'package.json').is_file(), spec
        packages.append(str(target))
    settings = {'packages': packages}
    if with_old:
        settings['editDiff'] = {'nativeEdit': True}
    else:
        settings['packages'].append(str(repo))
        settings['toolUi'] = {'enabled': True, 'tools': {'edit': {'enabled': True}, 'hashline': {'enabled': True}}}
    (agent / 'settings.json').write_text(json.dumps(settings))
    work = root / name
    work.mkdir()
    (work / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
    session = work / 'session.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(work / 'events.jsonl'))
    screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                          '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'edit',
                          'Run the local edit'], env, work, b'BASELINE_DONE', b'BASELINE_DONE')
    assert b'Failed to load extension' not in screen, screen[-2000:]
    return {
        'card': '\n'.join(extract_card(screen, work)),
        'results': results(session),
        'bytes': (work / 'notes.txt').read_bytes(),
    }


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-full-ab-') as directory:
    base = Path(directory)
    old = stack(base, 'old', True, False)
    new = stack(base, 'new', False, True)
    assert old['card'] == new['card'], '完整栈 Edit 卡片不同'
    assert old['results'] == new['results'], '完整栈工具结果不同'
    assert old['bytes'] == new['bytes'], '完整栈文件字节不同'
    evidence = repo / 'docs/evidence/full-stack-ab.json'
    evidence.write_text(json.dumps({
        'edit_card_equal': True,
        'tool_results_equal': True,
        'file_bytes_equal': True,
        'old_stack': 'all local extensions + old hashline-diff',
        'new_stack': 'all local extensions minus hashline-diff + pi-tool-ui',
    }, ensure_ascii=False, indent=2) + '\n')
    print('完整用户栈 A/B：卡片、工具结果与文件字节一致')
