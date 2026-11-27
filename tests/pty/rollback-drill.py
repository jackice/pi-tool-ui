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
provider = repo / 'tests/pty/read-t0-provider.ts'


def run(root, name, settings):
    work = root / name
    work.mkdir()
    (work / 'short.txt').write_text('alpha\nbeta\ngamma\n')
    agent = work / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps(settings))
    session = work / 'session.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_READ_CASE='basic', PI_TOOL_UI_PROBE_LOG=str(work / 'events.jsonl'),
               PI_TOOL_UI_PROBE_RENDER='0')
    screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                          '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'read',
                          'Run the local read'], env, work, b'READ_T0_DONE', b'READ_T0_DONE', rows=60)
    text = '\n'.join(render(screen, lines=60))
    result = None
    for line in session.read_text().splitlines():
        entry = json.loads(line)
        message = entry.get('message')
        if entry.get('type') == 'message' and isinstance(message, dict) and message.get('role') == 'toolResult':
            result = message
    assert result is not None
    return {'card': '╭─ Read' in text, 'load_error': 'Failed to load extension' in text,
            'content': result.get('content')}


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-rollback-') as directory:
    root = Path(directory)
    normal = {'packages': [str(repo)], 'toolUi': {'enabled': True, 'tools': {'read': {'enabled': True}}}}
    single_off = {'packages': [str(repo)], 'toolUi': {'enabled': True, 'tools': {'read': {'enabled': False}}}}
    global_off = {'packages': [str(repo)], 'toolUi': {'enabled': False, 'tools': {'read': {'enabled': True}}}}

    broken = root / 'broken-package'
    (broken / 'dist').mkdir(parents=True)
    (broken / 'package.json').write_text(json.dumps({'name': 'broken-pi-tool-ui', 'version': '0.0.0', 'type': 'module',
                                                     'pi': {'extensions': ['./dist/index.js']}}))
    (broken / 'dist/index.js').write_text("throw new Error('broken artifact');\n")
    corrupt = {'packages': [str(broken)], 'toolUi': {'enabled': True, 'tools': {'read': {'enabled': True}}}}

    stages = {
        'normal': run(root, 'normal', normal),
        'single_off': run(root, 'single-off', single_off),
        'global_off': run(root, 'global-off', global_off),
        'removed': run(root, 'removed', {'packages': [], 'toolUi': {'enabled': True, 'tools': {'read': {'enabled': True}}}}),
    }
    corrupt_work = root / 'corrupt'
    corrupt_work.mkdir()
    corrupt_agent = corrupt_work / 'agent'
    corrupt_agent.mkdir()
    (corrupt_agent / 'settings.json').write_text(json.dumps(corrupt))
    failed = subprocess.run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                             '--list-models', 'none'], env=dict(PATH=os.environ['PATH'], HOME=str(corrupt_work),
                                                               PI_CODING_AGENT_DIR=str(corrupt_agent), TERM='xterm-256color',
                                                               PI_TELEMETRY='0'), cwd=corrupt_work,
                            capture_output=True, text=True, timeout=30)
    assert 'Failed to load extension' in failed.stdout + failed.stderr
    assert stages['normal']['card'] is True and stages['normal']['load_error'] is False
    for name in ('single_off', 'global_off', 'removed'):
        assert stages[name]['card'] is False, name
    baseline = stages['normal']['content']
    for name in ('single_off', 'global_off', 'removed'):
        assert stages[name]['content'] == baseline, name
    evidence = repo / 'docs/evidence/rollback-drill.json'
    evidence.write_text(json.dumps({'pi_version': version, 'normal_card': True,
                                    'single_off_native': True, 'global_off_native': True,
                                    'corrupt_start_failed': True, 'removed_native': True,
                                    'content_equal': True, 'load_error_reported': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('回滚演练：单工具/全局关闭、损坏包启动失败、移除后回原生，content 一致；损坏包有 load error')
