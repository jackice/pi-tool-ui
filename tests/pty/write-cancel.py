import json
import os
from pathlib import Path
import subprocess
import tempfile

from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/write-cases-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-wcancel-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'write': {'enabled': True}}},
    }))
    log = root / 'events.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_WRITE_CASE='success', PI_WRITE_STREAM='1',
               PI_WRITE_TOKENS='1', PI_TOOL_UI_PROBE_LOG=str(log), PI_TOOL_UI_PROBE_RENDER='0')
    capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                 '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'write',
                 'Run the local write'], env, root, b'WRITE_DONE', b'', rows=60, stop=b'out.txt', interrupt=True)
    events = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    assert not (root / 'out.txt').exists(), '取消后仍写入文件'
    assert not any(item.get('event') == 'tool-execution' for item in events), events
    evidence = repo / 'docs/evidence/write-cancel.json'
    evidence.write_text(json.dumps({'pi_version': version, 'file_absent': True, 'executions': 0},
                                   ensure_ascii=False, indent=2) + '\n')
    print('Write 取消：参数流式阶段中断，未执行、未写入')
