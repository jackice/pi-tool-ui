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
provider = repo / 'tests/pty/bash-cases-provider.ts'
peer = repo / 'tests/pty/peer-bash.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-downstream-') as directory:
    root = Path(directory)
    observed = {}
    for enabled in (False, True):
        work = root / ('on' if enabled else 'off')
        work.mkdir()
        agent = work / 'agent'
        agent.mkdir()
        (agent / 'settings.json').write_text(json.dumps({
            'packages': [str(repo)],
            'toolUi': {'enabled': enabled, 'tools': {'bash': {'enabled': enabled}}},
        }))
        env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
                   PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE='success',
                   PI_TOOL_UI_PROBE_LOG=str(work / 'events.jsonl'), PI_TOOL_UI_PROBE_RENDER='0')
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                              '-e', str(provider), '-e', str(peer), '--model', 'tool-ui-probe/local',
                              '--tools', 'bash', 'Run the local bash'], env, work, b'BASH_DONE', b'BASH_DONE', rows=60)
        text = '\n'.join(render(screen))
        observed['on' if enabled else 'off'] = {
            'peer_visible': 'PEER_BASH' in text,
            'command_count': text.count("printf 'ok"),
        }
    assert observed['off']['peer_visible'] is True, observed
    assert observed['on']['peer_visible'] is True, observed
    assert observed['on']['command_count'] == 1, observed
    evidence = repo / 'docs/evidence/bash-downstream.json'
    evidence.write_text(json.dumps({'pi_version': version, **observed}, ensure_ascii=False, indent=2) + '\n')
    print('Bash 下游：OFF/ON 均返回后加载 PEER_BASH，原生命令仍只一次')
