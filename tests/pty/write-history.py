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

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-whistory-') as directory:
    root = Path(directory)
    creator = root / 'creator'
    creator.mkdir()
    (creator / 'settings.json').write_text('{}')
    session = root / 'session.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(creator), PI_WRITE_CASE='many',
               PI_TOOL_UI_PROBE_LOG=str(root / 'create.log'), PI_TOOL_UI_PROBE_RENDER='0')
    subprocess.run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                    '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'write', '--print', 'Run'],
                   cwd=root, env=env, capture_output=True, text=True, timeout=60, check=True)

    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'write': {'enabled': True}}},
    }))
    many = root / 'many.txt'
    if many.exists():
        many.write_text('changed\n')
    replay_log = root / 'replay.log'
    screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                          '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'write'],
                         dict(env, PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_RENDER='0',
                              PI_TOOL_UI_PROBE_LOG=str(replay_log)),
                         root, b'WRITE_DONE', b'\xe2\x9c\x93', rows=60)
    replayed = [json.loads(line) for line in replay_log.read_text().splitlines()] if replay_log.exists() else []
    assert not any(item.get('event') == 'tool-execution' for item in replayed), replayed
    text = '\n'.join(render(screen))
    assert '✓' in text, text[-600:]
    assert 'streaming' not in text, [line for line in text.split('\n') if 'streaming' in line]
    assert text.count('many.txt') == 1, text[-800:]
    assert 'line 1' in text and 'line 6' in text, text[-800:]
    assert 'line 7' not in text, text[-800:]
    assert 'changed' not in text, text[-800:]
    evidence = repo / 'docs/evidence/write-history.json'
    evidence.write_text(json.dumps({'pi_version': version, 'status_success': True, 'head_preview': True,
                                    'reexecuted': False, 'shows_saved': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('Write 历史：final 显示 ✓ 与 head 1–6，而非 streaming/tail')
