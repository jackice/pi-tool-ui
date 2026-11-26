import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/read-t0-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-rhistory-') as directory:
    root = Path(directory)
    (root / 'short.txt').write_text('alpha\nbeta\ngamma\n')
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text('{}')
    session = root / 'session.jsonl'
    create_log = root / 'create.log'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_READ_CASE='basic', PI_TOOL_UI_PROBE_LOG=str(create_log))
    capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                 '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'read', 'Run'],
                env, root, b'READ_T0_DONE', b'READ_T0_PROBE', rows=50)
    created = [json.loads(line) for line in create_log.read_text().splitlines()]
    original = next(item for item in created if item.get('event') == 'result' and not item['partial'])

    replay_log = root / 'replay.log'
    capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                 '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'read', 'Run'],
                dict(env, PI_TOOL_UI_PROBE_LOG=str(replay_log)), root, b'READ_T0_DONE', b'READ_T0_DONE', rows=50)
    replayed = [json.loads(line) for line in replay_log.read_text().splitlines()]
    final = next(item for item in replayed if item.get('event') == 'result' and not item['partial'])
    assert final['content'] == original['content']
    assert final.get('details') == original.get('details')
    evidence = repo / 'docs/evidence/read-history.json'
    evidence.write_text(json.dumps({'pi_version': version, 'content_equal': True, 'details_equal': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('Read 历史：content/details 与首次执行一致')
