import json
import os
import subprocess
from pathlib import Path
import shutil
import tempfile

from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
compressor = workspace / 'dotfiles/pi/.pi/agent/extensions/pi-shell-compressor'
provider = repo / 'tests/pty/bash-cases-provider.ts'


def run(root, enabled):
    work = root / ('on' if enabled else 'off')
    work.mkdir(parents=True)
    agent = work / 'agent'
    (agent / 'extensions').mkdir(parents=True)
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'bash': {'enabled': True}}},
    }))
    (work / '.pi/agent').mkdir(parents=True)
    shutil.copyfile(compressor / 'shell-compressor.json', work / '.pi/agent/shell-compressor.json')
    if enabled:
        shutil.copytree(compressor, agent / 'extensions/pi-shell-compressor')
    log = work / 'events.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE='compress', PI_TOOL_UI_PROBE_LOG=str(log))
    capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                          '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash', 'Run the local bash'],
                         env, work, b'BASH_DONE', b'BASH_PROBE')
    events = [json.loads(line) for line in log.read_text().splitlines()]
    final = next(item for item in events if item.get('event') == 'result' and not item['partial'])
    model = next(item for item in events if item.get('event') == 'model')
    text = '\n'.join(block.get('text', '') for block in final['content'] if block.get('type') == 'text')
    return {'text': text, 'details': final.get('details') or {}, 'model_tail': model['text'], 'error': final['error']}


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-seccomp-') as directory:
    root = Path(directory)
    on = run(root, True)
    off = run(root, False)
    assert on['text'].startswith('# shell-compressor'), on['text'][:120]
    assert 'shellCompressor' in on['details']
    assert not off['text'].startswith('# shell-compressor') and 'shellCompressor' not in off['details']
    assert 'same-line' in off['text'] and len(off['text'].splitlines()) == 500
    assert '# shell-compressor' in on['model_tail'] and '# shell-compressor' not in off['model_tail']
    evidence = repo / 'docs/evidence/security-compressor.json'
    evidence.write_text(json.dumps({'pi_version': version, 'product_on': True,
                                    'compressor_on': True, 'compressor_off': True,
                                    'model_sees_compressed': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('Compressor + 产品同开：ON 压缩/细节/模型一致；OFF 500 行')
