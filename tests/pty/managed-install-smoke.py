import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


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
