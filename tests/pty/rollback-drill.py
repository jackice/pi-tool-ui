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

tools = {
    'read': (repo / 'tests/pty/read-t0-provider.ts', 'PI_READ_CASE', 'basic', b'READ_T0_DONE', 'Read'),
    'write': (repo / 'tests/pty/write-cases-provider.ts', 'PI_WRITE_CASE', 'success', b'WRITE_DONE', 'Write'),
    'bash': (repo / 'tests/pty/bash-cases-provider.ts', 'PI_BASH_CASE', 'success', b'BASH_DONE', 'Bash'),
}


def run(root, name, settings, tool):
    provider, variable, case, done, label = tools[tool]
    work = root / f'{tool}-{name}'
    work.mkdir()
    (work / 'short.txt').write_text('alpha\nbeta\ngamma\n')
    (work / 'dir').mkdir()
    agent = work / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps(settings))
    session = work / 'session.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(work / 'events.jsonl'),
               PI_TOOL_UI_PROBE_RENDER='0', **{variable: case})
    screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                          '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', tool,
                          'Run the local tool'], env, work, done, done, rows=60)
    text = '\n'.join(render(screen, lines=60))
    result = None
    for line in session.read_text().splitlines():
        entry = json.loads(line)
        message = entry.get('message')
        if entry.get('type') == 'message' and isinstance(message, dict) and message.get('role') == 'toolResult':
            result = message
    assert result is not None
    return {
        'card': f'╭─ {label}' in text,
        'load_error': 'Failed to load extension' in text,
        'content': json.loads(json.dumps(result.get('content')).replace(str(work), '<ROOT>')),
        'files': {path.name: path.read_text() for path in work.iterdir() if path.suffix == '.txt'},
    }


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-rollback-') as directory:
    root = Path(directory)
    normal = {'packages': [str(repo)], 'toolUi': {'enabled': True, 'tools': {
        'read': {'enabled': True}, 'write': {'enabled': True}, 'bash': {'enabled': True}}}}
    def single_off(tool):
        return {'packages': [str(repo)], 'toolUi': {'enabled': True, 'tools': {
            'read': {'enabled': tool != 'read'}, 'write': {'enabled': tool != 'write'}, 'bash': {'enabled': tool != 'bash'}}}}
    global_off = {'packages': [str(repo)], 'toolUi': {'enabled': False, 'tools': {
        'read': {'enabled': True}, 'write': {'enabled': True}, 'bash': {'enabled': True}}}}
    removed = {'packages': [], 'toolUi': {'enabled': True, 'tools': {
        'read': {'enabled': True}, 'write': {'enabled': True}, 'bash': {'enabled': True}}}}

    stages = {}
    for tool in tools:
        stages[tool] = {
            'normal': run(root, 'normal', normal, tool),
            'single_off': run(root, 'single-off', single_off(tool), tool),
            'global_off': run(root, 'global-off', global_off, tool),
            'removed': run(root, 'removed', removed, tool),
        }
        baseline = stages[tool]['normal']['content']
        assert stages[tool]['normal']['card'] is True
        assert stages[tool]['normal']['load_error'] is False
        for name in ('single_off', 'global_off', 'removed'):
            assert stages[tool][name]['card'] is False, (tool, name)
            assert stages[tool][name]['content'] == baseline, (tool, name)
        assert stages[tool]['normal']['files'] == stages[tool]['single_off']['files'] == stages[tool]['global_off']['files'] == stages[tool]['removed']['files']

    broken = root / 'broken-package'
    (broken / 'dist').mkdir(parents=True)
    (broken / 'package.json').write_text(json.dumps({'name': 'broken-pi-tool-ui', 'version': '0.0.0', 'type': 'module',
                                                     'pi': {'extensions': ['./dist/index.js']}}))
    (broken / 'dist/index.js').write_text("throw new Error('broken artifact');\n")
    corrupt_work = root / 'corrupt'
    corrupt_work.mkdir()
    corrupt_agent = corrupt_work / 'agent'
    corrupt_agent.mkdir()
    (corrupt_agent / 'settings.json').write_text(json.dumps({'packages': [str(broken)], 'toolUi': {'enabled': True, 'tools': {'read': {'enabled': True}}}}))
    failed = subprocess.run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                             '--list-models', 'none'], env=dict(PATH=os.environ['PATH'], HOME=str(corrupt_work),
                                                               PI_CODING_AGENT_DIR=str(corrupt_agent), TERM='xterm-256color',
                                                               PI_TELEMETRY='0'), cwd=corrupt_work,
                            capture_output=True, text=True, timeout=30)
    assert 'Failed to load extension' in failed.stdout + failed.stderr
    recovered = {tool: run(root, f'recovered-{tool}', removed, tool) for tool in tools}
    for tool in tools:
        assert recovered[tool]['card'] is False
        assert recovered[tool]['content'] == stages[tool]['normal']['content']
        assert recovered[tool]['files'] == stages[tool]['normal']['files']

    evidence = repo / 'docs/evidence/rollback-drill.json'
    evidence.write_text(json.dumps({'pi_version': version, 'tools': list(tools),
                                    'normal_card': True, 'single_off_native': True,
                                    'global_off_native': True, 'removed_native': True,
                                    'content_equal': True, 'corrupt_start_failed': True,
                                    'corrupt_recovered_native': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('回滚演练：Bash/Write/Read 单工具/全局/移除回原生；损坏包失败，移除后恢复；content 一致')
