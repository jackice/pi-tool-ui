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

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-wcall-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'write': {'enabled': True}}},
    }))
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_WRITE_CASE='success', PI_WRITE_STREAM='1',
               PI_TOOL_UI_PROBE_LOG=str(root / 'events.jsonl'), PI_TOOL_UI_PROBE_RENDER='0')
    output = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                          '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'write',
                          'Run the local write'], env, root, b'WRITE_DONE', b'', rows=60, stop=b'alpha')
    text = '\n'.join(render(output, lines=60))
    card = '\n'.join(extract_card(output, root, lines=60))
    assert 'Write' in card and 'out.txt' in card and 'alpha' in card, card[-600:]
    evidence = repo / 'docs/evidence/write-call-stream.json'
    evidence.write_text(json.dumps({'pi_version': version, 'args_stream_preview': True, 'path': 'out.txt'},
                                   ensure_ascii=False, indent=2) + '\n')
    print('Write 参数流式预览：argsComplete=false 时已显示路径与正文')
