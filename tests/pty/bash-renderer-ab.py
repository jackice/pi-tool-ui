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
provider = repo / 'tests/pty/bash-cases-provider.ts'


def run(root, render):
    work = root / ('on' if render else 'off')
    work.mkdir(parents=True)
    agent = work / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text('{}')
    log = work / 'events.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE='write',
               PI_TOOL_UI_PROBE_LOG=str(log), PI_TOOL_UI_PROBE_RENDER='1' if render else '0')
    capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                 '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash', 'Run the local bash'],
                env, work, b'BASH_DONE', b'BASH_DONE')
    events = [json.loads(line) for line in log.read_text().splitlines()]
    finals = [item for item in events if item.get('event') == 'result' and not item['partial']]
    model = next(item for item in events if item.get('event') == 'model')
    return {
        'text': ('\n'.join(block.get('text', '') for block in finals[0]['content'] if block.get('type') == 'text')) if finals else None,
        'model_tail': model['tail'],
        'runs': sum(1 for item in events if item.get('event') == 'tool-execution'),
        'file': (work / 'out.txt').read_text(),
    }


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-renderer-') as directory:
    root = Path(directory)
    on = run(root, True)
    off = run(root, False)
    assert on['runs'] == off['runs'] == 1, (on['runs'], off['runs'])
    assert on['file'] == off['file'] == 'ok\n'
    assert on['text'] == '(no output)', on['text']
    assert 'no output' in on['model_tail'] and 'no output' in off['model_tail']
    assert ('shellCompressor' in off['model_tail']) == ('shellCompressor' in on['model_tail'])
    evidence = repo / 'docs/evidence/bash-renderer-ab.json'
    evidence.write_text(json.dumps({
        'runs_on': 1, 'runs_off': 1, 'file_equal': True, 'final_text_equal': True,
    }, ensure_ascii=False, indent=2) + '\n')
    print('Bash renderer OFF/ON：各执行一次，文件与 final 文本一致')
