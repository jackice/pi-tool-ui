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
probe = repo / 'tests/pty/bash-slot-c-probe.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-slotc-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text('{}')
    log = root / 'events.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(log))
    screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                          '-e', str(probe), '--model', 'tool-ui-probe/local', '--tools', 'bash',
                          'Run the local bash'], env, root, b'SLOT_C_DONE', b'SLOT_C_DONE')
    events = [json.loads(line) for line in log.read_text().splitlines()]
    results = [item for item in events if item['event'] == 'result']
    assert all(item['shell'] == 'default' for item in results), results
    assert screen.count(b"CUSTOM_OUT") == 1, screen.count(b"CUSTOM_OUT")
    assert screen.count(b"printf 'ok") == 1, screen.count(b"printf 'ok")
    evidence = repo / 'docs/evidence/bash-slot-c.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'candidate': 'C',
        'native_shell_preserved': True,
        'command_once': True,
        'custom_output_once': True,
    }, ensure_ascii=False, indent=2) + '\n')
    print('Bash slot 候选 C：保留原生 shell/call，仅替换 result；命令仅出现一次')
