import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from terminal import run_tui


def run(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr


pi = shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
with tempfile.TemporaryDirectory(prefix='pi-tool-ui-managed-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    env = dict(PATH=os.environ['PATH'], HOME=directory, TERM='xterm-256color',
               PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0')
    spec = 'npm:@jackice/pi-session-todo@0.1.2'
    env.update(npm_config_fetch_retries='0', npm_config_fetch_timeout='12000')
    print(run([pi, 'install', spec], root, env).strip())
    assert spec in json.loads((agent / 'settings.json').read_text())['packages']
    modules = agent / 'npm/node_modules'
    package = modules / '@jackice/pi-session-todo'
    manifest = json.loads((package / 'package.json').read_text())
    assert manifest['version'] == '0.1.2' and manifest['peerDependencies'], manifest
    libraries = list(modules.rglob('@jackice/pi-ui/package.json'))
    assert libraries and {json.loads(path.read_text())['version'] for path in libraries} == {'0.4.2'}, libraries
    assert not list(modules.rglob('@earendil-works/pi-*/package.json')), '受管安装树含第二套 Pi runtime'
    output = run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--help'], root, env)
    assert '--session-todo-hide-ms' in output and 'Failed to load extension' not in output, output
    print('Pi 1.6.0 受管安装：扩展注册 CLI flag，pi-ui@0.4.2 可用，未安装宿主 peers')

    installed = Path(os.environ.get('PI_TOOL_UI_STACK_MODULES', Path.home() / '.pi/agent/npm/node_modules'))
    settings_file = agent / 'settings.json'
    settings = json.loads(settings_file.read_text())
    nested_ui = package / 'node_modules/@jackice/pi-ui'
    nested_ui.parent.mkdir(parents=True, exist_ok=True)
    (modules / '@jackice/pi-ui').rename(nested_ui)
    for name, version in {
        '@jackice/hashline': '0.1.2',
        '@jackice/pi-approval-gate': '0.1.6',
        '@jackice/pi-prompt': '0.2.1',
        '@jackice/pi-ui': '0.5.0',
        '@oh-my-pi/pi-utils': '17.2.12',
        '@oh-my-pi/pi-natives': '17.2.12',
        '@oh-my-pi/pi-natives-darwin-arm64': '17.2.12',
    }.items():
        source = installed / name
        assert json.loads((source / 'package.json').read_text())['version'] == version, name
        target = modules / name
        shutil.copytree(source, target)
        if name in ('@jackice/hashline', '@jackice/pi-approval-gate', '@jackice/pi-prompt'):
            settings['packages'].append(str(target))
    settings_file.write_text(json.dumps(settings))
    workspace = Path(__file__).resolve().parents[3]
    compressor = workspace / 'dotfiles/pi/.pi/agent/extensions/pi-shell-compressor'
    shutil.copytree(compressor, agent / 'extensions/pi-shell-compressor')
    home_agent = root / '.pi/agent'
    home_agent.mkdir(parents=True)
    shutil.copyfile(compressor / 'shell-compressor.json', home_agent / 'shell-compressor.json')
    assert not list(modules.rglob('@earendil-works/pi-*/package.json')), '共装树含第二套 Pi runtime'
    output = run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--help'], root, env)
    assert '--session-todo-hide-ms' in output and '--approval-guard' in output, output
    assert 'Failed to load extension' not in output, output
    probe = Path(__file__).with_name('probe.ts').resolve()
    log = root / 'events.jsonl'
    (root / 'fixture.txt').write_text('fixture from isolated cwd\n')
    output = run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session', '--print',
                  '-e', str(probe), '--model', 'tool-ui-probe/local', '--tools', 'read', 'Run the local fixture'],
                 root, dict(env, PI_TOOL_UI_PROBE_LOG=str(log)))
    assert 'PROBE_DONE' in output and 'Failed to load extension' not in output, output
    assert [json.loads(line) for line in log.read_text().splitlines()] == [
        {'event': 'session', 'hasUI': False}, {'event': 'tool-execution'},
    ]
    print('隔离核心栈：无旧 Diff，原生 Read 正常，未触发 renderer')

    log.unlink()
    assert not (agent / 'extensions/hashline-diff').exists()
    command = [pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
               '-e', str(probe), '--model', 'tool-ui-probe/local', '--tools', 'read', 'Run the local fixture']
    probe_env = dict(env, PI_TOOL_UI_PROBE_LOG=str(log))
    run_tui(command, probe_env, root, b'PROBE_RESULT')
    events = [json.loads(line) for line in log.read_text().splitlines()]
    final = next(item for item in events if item['event'] == 'result' and not item['partial'])
    text = final['content'][0]['text']
    assert 'fixture.txt#' in text and '1:fixture from isolated cwd' in text, final
    assert sum(item['event'] == 'tool-execution' for item in events) == 1, events

    log.unlink()
    peer = probe.with_name('peer.ts')
    screen = run_tui([*command[:-1], '-e', str(peer), command[-1]],
                     dict(probe_env, PI_TOOL_UI_PROBE_PASS='1'), root, b'PEER_RESULT')
    assert b'PROBE_RESULT' not in screen
    events = [json.loads(line) for line in log.read_text().splitlines()]
    assert [item['event'] for item in events if item['event'].endswith('-enter')] == [
        'probe-enter', 'peer-enter',
    ], events
    print('核心栈 TUI：Hashline 改写后的 final 到达 renderer，透传保留自定义下游')
