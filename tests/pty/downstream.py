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
provider = repo / 'tests/pty/edit-provider.ts'
peer = repo / 'tests/pty/peer-edit.ts'


def run_case(root, enabled):
    root.mkdir(parents=True, exist_ok=True)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': enabled, 'tools': {'edit': {'enabled': enabled}}},
    }))
    (root / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color',
               PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0',
               PI_TOOL_UI_PROBE_LOG=str(root / 'events.jsonl'))
    return capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                        '-e', str(provider), '-e', str(peer), '--model', 'tool-ui-probe/local',
                        '--tools', 'edit', 'Run the local edit'], env, root, b'BASELINE_DONE', b'BASELINE_DONE')


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-downstream-') as directory:
    base = Path(directory)
    off = run_case(base / 'off', False)
    assert b'PEER_EDIT' in off, '关闭时未返回自定义下游'
    on = run_case(base / 'on', True)
    assert b'PEER_EDIT' in on, '该加载顺序下后加载 renderer 应继续生效'
    took_over = False
    evidence = repo / 'docs/evidence/downstream.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({
        'off_returns_downstream': True,
        'on_takes_over': took_over,
        'load_order': 'settings package before explicit -e peer',
    }, ensure_ascii=False, indent=2) + '\n')
    print(f"自定义下游：OFF 保留 PEER_EDIT；ON {'接管' if took_over else '仍保留下游'}")
