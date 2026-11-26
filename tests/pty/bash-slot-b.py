import json
import os
from pathlib import Path
import shutil
import tempfile

from terminal import capture_tui


pi = shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
probe = repo / 'tests/pty/bash-slot-b-probe.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-slotb-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text('{}')
    log = root / 'events.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(log))
    screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                          '-e', str(probe), '--model', 'tool-ui-probe/local', '--tools', 'bash', 'Run the local bash'],
                         env, root, b'SLOT_DONE', b'SLOT_DONE')
    events = [json.loads(line) for line in log.read_text().splitlines()]
    results = [item for item in events if item['event'] == 'result']
    assert all(item['shared'] for item in results), results
    assert screen.count(b'BASH_TOP') == 1 and screen.count(b'BASH_BOTTOM') == 1, (screen.count(b'BASH_TOP'), screen.count(b'BASH_BOTTOM'))
    assert screen.find(b'BASH_TOP') < screen.find(b'BASH_BOTTOM')
    assert screen.count(b'\xe2\x95\xad') == 1 and screen.count(b'\xe2\x95\xb0') == 1, (screen.count(b'\xe2\x95\xad'), screen.count(b'\xe2\x95\xb0'))
    assert screen.find(b'\xe2\x95\xad') < screen.find(b'BASH_BOTTOM') < screen.find(b'\xe2\x95\xb0')
    evidence = repo / 'docs/evidence/bash-slot.json'
    data = json.loads(evidence.read_text())
    data['candidate_b'] = {'chosen': True, 'single_top_and_bottom': True, 'single_border': True, 'shared_state': True}
    evidence.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print('Bash slot 候选 B：call/result 各渲染一部分，各一次且顺序正确，共享状态')
