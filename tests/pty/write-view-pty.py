import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from screen import extract_card, render
from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/write-cases-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-writeview-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'write': {'enabled': True}}},
    }))
    observed = {}
    for case in ('success', 'many', 'error'):
        work = root / case
        work.mkdir()
        (work / 'dir').mkdir()
        env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
                   PI_CODING_AGENT_DIR=str(agent), PI_WRITE_CASE=case,
                   PI_TOOL_UI_PROBE_LOG=str(work / 'events.jsonl'), PI_TOOL_UI_PROBE_RENDER='0')
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                              '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'write',
                              'Run the local write'], env, work, b'WRITE_DONE', b'WRITE_DONE', rows=60)
        text = '\n'.join(render(screen))
        try:
            card = '\n'.join(extract_card(screen, work))
        except (ValueError, StopIteration):
            card = text
        observed[case] = {'text': text, 'card': card}

    print('HAS_WRITE', 'Write' in observed['success']['text'])
    assert 'Write' in observed['success']['card'] and '✓' in observed['success']['card'], observed['success']['text'][-800:]
    assert observed['success']['text'].count('out.txt') == 1
    assert observed['success']['text'].count('alpha') == 1 and observed['success']['text'].count('beta') == 1
    assert 'line 1' in observed['many']['card'] and 'line 6' in observed['many']['card']
    assert 'line 7' not in observed['many']['card']
    assert '✗' in observed['error']['card']
    assert 'line 1' not in observed['error']['card']
    evidence = repo / 'docs/evidence/write-view.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'path_once': True,
        'head_preview_6': True,
        'error_hides_content': True,
    }, ensure_ascii=False, indent=2) + '\n')
    print('WriteView 接线：标题/路径一次、head 6 行、错误隐藏正文')
