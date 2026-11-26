import json
import os
from pathlib import Path
import shutil
import tempfile

from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
probe = repo / 'tests/pty/bash-slot-probe.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-slot-') as directory:
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
    events = [json.loads(line) for line in log.read_text().splitlines() if 'event' in line]
    calls = [item for item in events if item['event'] == 'call']
    results = [item for item in events if item['event'] == 'result']
    final_index = max(index for index, item in enumerate(events) if item['event'] == 'result' and not item['partial'])
    assert not any(item['event'] == 'call' and index > final_index for index, item in enumerate(events)), events
    assert not any(item['event'] == 'call' and item['final'] for item in events), events
    assert {item['pad'] for item in calls} == {1}, calls
    assert all(not item['partial'] for item in results[-1:]) and any(item['partial'] for item in results)
    assert screen.count(b'BASH_CARD_CALL') == 1, screen.count(b'BASH_CARD_CALL')
    evidence = repo / 'docs/evidence/bash-slot.json'
    evidence.write_text(json.dumps({
        'candidate': 'A-rejected',
        'call_rerendered_after_final': False,
        'shared_state': True,
        'single_card': True,
        'output_pad': 1,
        'events': events,
    }, ensure_ascii=False, indent=2) + '\n')
    print('Bash slot 候选 A：确认 final 后无 call 重绘；共享 state 与单卡片成立，A 否决')
