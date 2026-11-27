import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'


def run_rpc(work, agent, provider, tool, variable, case):
    session = work / 'session.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(work / 'events.jsonl'),
               PI_TOOL_UI_PROBE_RENDER='0', **{variable: case})
    process = subprocess.Popen([pi, '--mode', 'rpc', '--session', str(session),
                                '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', tool],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=work, env=env, text=True)
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(json.dumps({'id': 'p1', 'type': 'prompt', 'message': 'Run the local tool'}) + '\n')
    process.stdin.flush()
    deadline = time.monotonic() + 30
    settled = False
    while time.monotonic() < deadline:
        line = process.stdout.readline()
        if line == '':
            break
        if 'agent_settled' in line:
            settled = True
            break
    process.stdin.close()
    process.wait(timeout=10)
    assert process.returncode == 0, process.stderr.read()
    assert settled, 'RPC 未收到 agent_settled'
    return session


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-rpc-') as directory:
    root = Path(directory)
    cases = [('read', repo / 'tests/pty/read-t0-provider.ts', 'PI_READ_CASE', 'basic'),
             ('write', repo / 'tests/pty/write-cases-provider.ts', 'PI_WRITE_CASE', 'success'),
             ('bash', repo / 'tests/pty/bash-cases-provider.ts', 'PI_BASH_CASE', 'success')]
    observed = {}
    for tool, provider, variable, case in cases:
        for enabled in (False, True):
            work = root / f'{tool}-{"on" if enabled else "off"}'
            work.mkdir()
            (work / 'short.txt').write_text('alpha\nbeta\ngamma\n')
            agent = work / 'agent'
            agent.mkdir()
            (agent / 'settings.json').write_text(json.dumps({
                'packages': [str(repo)] if enabled else [],
                'toolUi': {'enabled': enabled, 'tools': {tool: {'enabled': enabled}}},
            }))
            session = run_rpc(work, agent, provider, tool, variable, case)
            messages = []
            for line in session.read_text().splitlines():
                entry = json.loads(line)
                message = entry.get('message')
                if entry.get('type') == 'message' and isinstance(message, dict) and message.get('role') == 'toolResult':
                    messages.append(message)
            assert messages, (tool, enabled)
            result = messages[-1]
            observed[f'{tool}-{"on" if enabled else "off"}'] = {
                'content': json.loads(json.dumps(result.get('content')).replace(str(work), '<ROOT>')),
                'details': json.loads(json.dumps(result.get('details')).replace(str(work), '<ROOT>')),
                'files': {path.name: path.read_text() for path in work.iterdir() if path.suffix == '.txt'},
            }
    for tool, _, _, _ in cases:
        on = observed[f'{tool}-on']; off = observed[f'{tool}-off']
        assert on['content'] == off['content'], tool
        assert on['details'] == off['details'], tool
        assert on['files'] == off['files'], tool
    evidence = repo / 'docs/evidence/rpc-ab.json'
    evidence.write_text(json.dumps({'pi_version': version, 'read': True, 'write': True, 'bash': True,
                                    'content_details_files_equal': True, 'agent_settled': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('RPC A/B：Read/Write ON/OFF content/details/files 一致，agent_settled 正常')
