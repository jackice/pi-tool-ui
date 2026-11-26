import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from screen import extract_card
from terminal import capture_tui


pi = shutil.which('pi')
npm = shutil.which('npm')
assert pi and npm, '需要 Pi 1.6.0 与 npm'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
old = workspace / 'dotfiles/pi/.pi/agent/extensions/hashline-diff'
library = old / 'node_modules/@jackice/pi-ui'
provider = repo / 'tests/pty/edit-provider.ts'
golden = (repo / 'tests/fixtures/migration/edit-native-0.5.1.txt').read_text().rstrip('\n')

env_base = dict(PATH=os.environ['PATH'], TERM='xterm-256color', PI_TELEMETRY='0')


def run(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr


def install_old(agent):
    shutil.copytree(old, agent / 'extensions/hashline-diff', ignore=shutil.ignore_patterns('node_modules'))
    (agent / 'extensions/hashline-diff/node_modules/@jackice').mkdir(parents=True)
    shutil.copytree(library, agent / 'extensions/hashline-diff/node_modules/@jackice/pi-ui')


def session_results(session):
    results = []
    for line in session.read_text().splitlines():
        entry = json.loads(line)
        message = entry.get('message', {})
        if entry.get('type') == 'message' and message.get('role') == 'toolResult':
            results.append([block.get('text', '') for block in message.get('content', [])])
    return results


def scenario(root, agent, session, settings):
    agent.mkdir(parents=True, exist_ok=True)
    (agent / 'settings.json').write_text(json.dumps(settings))
    (root / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
    env = dict(env_base, HOME=str(root), PI_CODING_AGENT_DIR=str(agent),
               PI_TOOL_UI_PROBE_LOG=str(root / 'events.jsonl'))
    screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                          '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'edit',
                          'Run the local edit'], env, root, b'BASELINE_DONE', b'BASELINE_DONE')
    return screen, (root / 'notes.txt').read_bytes(), session_results(session)


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-matrix-') as directory:
    root = Path(directory)
    env = dict(env_base, HOME=directory)

    # 1) 干净 checkout 必须能通过 prepack 产出 dist 入口。
    clone = root / 'clone'
    run(['git', 'clone', '-q', str(repo), str(clone)], root, env)
    run([npm, 'ci', '--legacy-peer-deps', '--no-audit', '--no-fund', '--fetch-retries=0'], clone, env)
    clean_pack = json.loads(run([npm, 'pack', '--json', '--pack-destination', str(root)], clone, env))[0]
    packed = {file['path'] for file in clean_pack['files']}
    assert {'dist/index.js', 'dist/config.js', 'package.json'} <= packed, packed

    # 2) 真实 tarball 安装；生产依赖树不含 Pi runtime。
    tarball = root / clean_pack['filename']
    install = root / 'install'
    install.mkdir()
    run([npm, 'install', '--legacy-peer-deps', '--no-audit', '--no-fund', '--fetch-retries=0', str(tarball)], install, env)
    package = install / 'node_modules/@jackice/pi-tool-ui'
    assert (package / 'dist/index.js').is_file()
    tree = run([npm, 'ls', '--all'], install, env)
    assert '@earendil-works/pi-coding-agent' not in tree and '@earendil-works/pi-tui' not in tree, tree

    # 3) 旧扩展与新包等价：文件字节、工具结果文本、卡片。
    old_screen, old_bytes, old_results = scenario(root / 'old', root / 'old-agent', root / 'old.jsonl',
                                                  {'editDiff': {'nativeEdit': True}})
    new_root = root / 'new'
    new_root.mkdir()
    new_agent = new_root / 'agent'
    new_screen, new_bytes, new_results = scenario(new_root, new_agent, root / 'new.jsonl',
                                                  {'packages': [str(package)], 'editDiff': {'nativeEdit': True}})
    new_card = '\n'.join(extract_card(new_screen, new_root))
    assert new_card == golden, new_card
    assert old_bytes == new_bytes and old_results == new_results, (old_bytes, new_bytes, old_results, new_results)

    # 4) 双加载：旧目录存在时新包拒绝接管。
    dual = root / 'dual'
    (dual / 'agent').mkdir(parents=True)
    install_old(dual / 'agent')
    (dual / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
    dual_env = dict(env_base, HOME=str(dual), PI_CODING_AGENT_DIR=str(dual / 'agent'),
                    PI_TOOL_UI_PROBE_LOG=str(dual / 'events.jsonl'))
    (dual / 'agent/settings.json').write_text(json.dumps({'packages': [str(package)], 'editDiff': {'nativeEdit': True}}))
    screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                          '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'edit',
                          'Run the local edit'], dual_env, dual, b'BASELINE_DONE', b'BASELINE_DONE')
    assert b'Edit' not in screen, '双加载时新包仍然接管'

    evidence = repo / 'docs/evidence/tarball-matrix.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({
        'clean_pack': sorted(path for path in packed if path.startswith('dist/')),
        'tarball_install': True,
        'no_pi_runtime': True,
        'file_bytes_equal': True,
        'tool_results_equal': True,
        'card_matches_golden': True,
        'dual_load_disabled': True,
    }, ensure_ascii=False, indent=2) + '\n')
    print('干净打包 + tarball 安装：入口/依赖树/等价/双加载均通过')
