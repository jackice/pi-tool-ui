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
provider = repo / 'tests/pty/read-t0-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-rshow-') as directory:
    root = Path(directory)
    (root / 'pixel.png').write_bytes(bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cf0000040001ff9f2e2d0000000049454e44ae426082'))
    observed = {}
    for show in (False, True):
        work = root / ('on' if show else 'off'); work.mkdir()
        agent = work / 'agent'; agent.mkdir()
        (agent / 'settings.json').write_text(json.dumps({'terminal': {'showImages': show}}))
        for name in ('pixel.png',):
            shutil.copyfile(root / name, work / name)
        log = work / 'events.jsonl'
        env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
                   PI_CODING_AGENT_DIR=str(agent), PI_READ_CASE='image', PI_READ_VISION='1',
                   PI_TOOL_UI_PROBE_LOG=str(log))
        capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                     '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'read',
                     'Run the local read'], env, work, b'READ_T0_DONE', b'READ_T0_PROBE', rows=50)
        events = [json.loads(line) for line in log.read_text().splitlines()]
        observed['on' if show else 'off'] = next(item for item in events if item.get('event') == 'result')['showImages']
    assert observed == {'on': True, 'off': False}, observed
    evidence = repo / 'docs/evidence/read-show-images.json'
    evidence.write_text(json.dumps({'pi_version': version, 'showImages': observed, 'owner': 'native renderer'},
                                   ensure_ascii=False, indent=2) + '\n')
    print('Read showImages：渲染上下文 true/false 与设置一致，图片仍归原生')
