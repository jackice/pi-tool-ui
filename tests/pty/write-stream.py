import json
import os
from pathlib import Path
import shutil
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

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-wstream-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text('{}')
    log = root / 'events.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_WRITE_CASE='success', PI_WRITE_STREAM='1',
               PI_TOOL_UI_PROBE_LOG=str(log))
    capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                 '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'write',
                 'Run the local write'], env, root, b'WRITE_DONE', b'WRITE_PROBE', rows=50)
    events = [json.loads(line) for line in log.read_text().splitlines()]
    calls = [item for item in events if item.get('event') == 'call']
    incomplete = [item for item in calls if item.get('argsComplete') is False]
    final = [item for item in events if item.get('event') == 'result' and not item['partial']][-1]
    assert incomplete, calls
    assert any(isinstance(item['args'].get('content'), str) for item in incomplete), incomplete[:3]
    assert final['args']['content'] == 'alpha\nbeta\n'
    evidence = repo / 'docs/evidence/write-stream.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'incomplete_calls': len(incomplete),
        'first_args': incomplete[0]['args'],
        'final_content': final['args']['content'],
    }, ensure_ascii=False, indent=2) + '\n')
    print(f'Write 流式参数：{len(incomplete)} 次 argsComplete=false 快照，final 内容正确')
