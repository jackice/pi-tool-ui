import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
read_provider = repo / 'tests/pty/read-t0-provider.ts'
write_provider = repo / 'tests/pty/write-cases-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-headless-') as directory:
    root = Path(directory)
    observed = {}
    cases = [('read', 'basic', read_provider, 'PI_READ_CASE'), ('read', 'truncated', read_provider, 'PI_READ_CASE'),
             ('write', 'success', write_provider, 'PI_WRITE_CASE'), ('write', 'error', write_provider, 'PI_WRITE_CASE')]
    for tool, case, provider, variable in cases:
        for enabled in (False, True):
            work = root / f'{tool}-{case}-{"on" if enabled else "off"}'
            work.mkdir()
            (work / 'short.txt').write_text('alpha\nbeta\ngamma\n')
            (work / 'long.txt').write_text(''.join(f'line {index}\n' for index in range(1, 2101)))
            (work / 'dir').mkdir()
            agent = work / 'agent'
            agent.mkdir()
            settings = {'packages': [str(repo)] if enabled else [], 'toolUi': {'enabled': enabled, 'tools': {tool: {'enabled': enabled}}}}
            (agent / 'settings.json').write_text(json.dumps(settings))
            log = work / 'events.jsonl'
            session = work / 'session.jsonl'
            env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
                       PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(log), PI_TOOL_UI_PROBE_RENDER='0',
                       **{variable: case})
            result = subprocess.run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                                     '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', tool,
                                     '--print', 'Run the local tool'], env=env, cwd=work, capture_output=True, text=True, timeout=60)
            assert result.returncode == 0, result.stdout + result.stderr
            events = [json.loads(line) for line in log.read_text().splitlines()]
            final = None
            for line in session.read_text().splitlines():
                entry = json.loads(line)
                message = entry.get('message')
                if entry.get('type') == 'message' and isinstance(message, dict) and message.get('role') == 'toolResult':
                    final = message
            assert final is not None, (tool, case, enabled)
            files = {path.name: path.read_text() for path in work.iterdir() if path.suffix == '.txt'}
            observed[f'{tool}-{case}-{"on" if enabled else "off"}'] = {
                'content': json.loads(json.dumps(final.get('content')).replace(str(work), '<ROOT>')),
                'details': json.loads(json.dumps(final.get('details')).replace(str(work), '<ROOT>')),
                'executions': sum(1 for item in events if item.get('event') == 'tool-execution'),
                'files': files,
            }

    for tool, case, _, _ in cases:
        on = observed[f'{tool}-{case}-on']; off = observed[f'{tool}-{case}-off']
        assert on['content'] == off['content'], (tool, case, on['content'], off['content'])
        assert on['details'] == off['details'], (tool, case)
        assert on['executions'] == off['executions'] == 1, (tool, case)
        assert on['files'] == off['files'], (tool, case)
    evidence = repo / 'docs/evidence/headless-ab.json'
    evidence.write_text(json.dumps({'pi_version': version, 'read_basic': True, 'read_truncated': True,
                                    'write_success': True, 'write_error': True,
                                    'content_details_files_equal': True, 'runs': 1},
                                   ensure_ascii=False, indent=2) + '\n')
    print('Headless --print A/B：Read/Write 的 content/details/files 一致，各执行一次')
