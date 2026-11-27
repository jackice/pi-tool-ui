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
provider = repo / 'tests/pty/write-cases-provider.ts'


def copy_extension(target):
    target.mkdir(parents=True)
    shutil.copyfile(repo / 'package.json', target / 'package.json')
    shutil.copytree(repo / 'dist', target / 'dist')
    (target / 'node_modules/@jackice').mkdir(parents=True)
    shutil.copytree(repo / 'node_modules/@jackice/pi-ui', target / 'node_modules/@jackice/pi-ui')


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-dupload-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    extensions = agent / 'extensions'
    copy_extension(extensions / 'product-a')
    copy_extension(extensions / 'product-b')
    (agent / 'settings.json').write_text(json.dumps({'toolUi': {'enabled': True, 'tools': {'write': {'enabled': True}}}}))
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_WRITE_CASE='success',
               PI_TOOL_UI_PROBE_LOG=str(root / 'events.jsonl'), PI_TOOL_UI_PROBE_RENDER='0')
    screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                          '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'write',
                          'Run the local write'], env, root, b'WRITE_DONE', b'WRITE_DONE', rows=60)
    text = '\n'.join(render(screen, lines=60))
    assert 'Failed to load extension' not in text, text[-2000:]
    assert text.count('╭─ Write') == 1, text[-1200:]
    assert text.count('out.txt') == 1, text[-1200:]
    assert text.count('alpha') == 1 and text.count('beta') == 1, text[-1200:]
    evidence = repo / 'docs/evidence/duplicate-load.json'
    evidence.write_text(json.dumps({'pi_version': version, 'products_loaded': 2, 'cards': 1,
                                    'path_once': True, 'content_once': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('重复加载产品：双扩展注册后仍单卡片、path/正文各一次，无加载错误')
