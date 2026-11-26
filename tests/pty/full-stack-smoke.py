import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


pi = shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
live = Path.home() / '.pi/agent'
installed = live / 'npm/node_modules'


def run(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-full-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    shutil.copytree(workspace / 'dotfiles/pi/.pi/agent/extensions', agent / 'extensions')
    shutil.rmtree(agent / 'extensions/hashline-diff')
    for config in ('pi-prompt.json', 'shell-compressor.json', 'keybindings.json'):
        shutil.copyfile(live / config, agent / config)
    packages = []
    for spec in json.loads((live / 'settings.json').read_text())['packages']:
        name = spec.removeprefix('npm:')
        if '@' in name[1:]:
            name = name[:name.rindex('@')]
        target = installed / name
        assert (target / 'package.json').is_file(), spec
        packages.append(str(target))
    (agent / 'settings.json').write_text(json.dumps({'packages': packages}))
    env = dict(PATH=os.environ['PATH'], HOME=directory, TERM='xterm-256color',
               PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0')
    output = run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--help'], root, env)
    assert 'Failed to load extension' not in output, output
    for flag in ('--session-todo-hide-ms', '--approval-guard', '--handoff-auto-save'):
        assert flag in output, (flag, output)
    (root / 'fixture.txt').write_text('fixture from isolated cwd\n')
    log = root / 'events.jsonl'
    probe = Path(__file__).with_name('probe.ts').resolve()
    output = run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session', '--print',
                  '-e', str(probe), '--model', 'tool-ui-probe/local', '--tools', 'read', 'Run the local fixture'],
                 root, dict(env, PI_TOOL_UI_PROBE_LOG=str(log)))
    assert 'PROBE_DONE' in output and 'Failed to load extension' not in output, output
    assert [json.loads(line) for line in log.read_text().splitlines()] == [
        {'event': 'session', 'hasUI': False}, {'event': 'tool-execution'},
    ]
    log.unlink()
    from terminal import run_tui
    run_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
             '-e', str(probe), '--model', 'tool-ui-probe/local', '--tools', 'read', 'Run the local fixture'],
            dict(env, PI_TOOL_UI_PROBE_LOG=str(log)), root, b'PROBE_RESULT')
    events = [json.loads(line) for line in log.read_text().splitlines()]
    final = next(item for item in events if item['event'] == 'result' and not item['partial'])
    assert 'fixture.txt#' in final['content'][0]['text'], final
    print('完整用户扩展栈：离线加载无失败，CLI flag 齐全，Hashline 改写的 Read 正常')
