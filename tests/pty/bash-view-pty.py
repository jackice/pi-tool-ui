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
provider = repo / 'tests/pty/bash-cases-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-bashview-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'bash': {'enabled': True}}},
    }))
    observed = {}
    for case in ('success', 'lines', 'error', 'rows20'):
        log = root / f'{case}.jsonl'
        env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
                   PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE=case,
                   PI_TOOL_UI_PROBE_LOG=str(log), PI_TOOL_UI_PROBE_RENDER='0')
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                              '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash',
                              'Run the local bash'], env, root, b'BASH_DONE', b'BASH_DONE',
                              key=b'\x0f' if case == 'rows20' else None, rows=60)
        text = '\n'.join(render(screen))
        try:
            card = '\n'.join(extract_card(screen, root))
        except (ValueError, StopIteration):
            card = text
        observed[case] = {'screen': screen, 'card': card, 'text': text}

    assert 'Bash' in observed['success']['card'] and '✓' in observed['success']['card'], 'success-card'
    print('COUNT', observed['success']['text'].count("printf"), 'HAS', 'printf' in observed['success']['text'])
    assert observed['success']['text'].count("printf 'ok") == 1, observed['success']['text'][-400:]
    assert 'ok' in observed['success']['card']
    assert '2100' in observed['lines']['card'] and 'truncated' in observed['lines']['card'], 'lines-card'
    assert '✗' in observed['error']['card'], 'error-card'
    assert 'more rows' not in observed['rows20']['card'], observed['rows20']['card'][-300:]
    assert '1' in observed['rows20']['card'] and '20' in observed['rows20']['card'], observed['rows20']['card'][-300:]
    evidence = repo / 'docs/evidence/bash-view.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'cases': {case: {'card': value['card']} for case, value in observed.items()},
    }, ensure_ascii=False, indent=2) + '\n')
    print('BashView 接线：成功/截断/错误卡片、命令一次、截断提示与错误 glyph 通过')
