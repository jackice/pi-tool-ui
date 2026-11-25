import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def run(args, cwd, env):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=35)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


pi = shutil.which('pi')
npm = shutil.which('npm')
assert pi and npm, '需要 Pi 1.6.0 和 npm'
with tempfile.TemporaryDirectory(prefix='pi-tool-ui-pack-') as directory:
    root = Path(directory)
    source = root / 'source'
    dist = source / 'dist'
    dist.mkdir(parents=True)
    manifest = {
        'name': 'pi-tool-ui-loader-probe', 'version': '0.0.0', 'type': 'module',
        'files': ['dist'], 'pi': {'extensions': ['./dist/index.js']},
        'dependencies': {'@jackice/pi-ui': '0.4.2'},
        'peerDependencies': {'@earendil-works/pi-coding-agent': '1.6.0', '@earendil-works/pi-tui': '1.6.0'},
    }
    (source / 'package.json').write_text(json.dumps(manifest))
    (dist / 'index.js').write_text('''
import { getLanguageFromPath } from '@earendil-works/pi-coding-agent';
import { Text, visibleWidth } from '@earendil-works/pi-tui';
import { EditView } from '@jackice/pi-ui';

export default function () {
  if (getLanguageFromPath('fixture.ts') !== 'typescript' || visibleWidth('中') !== 2 ||
      !new Text('fixture', 0, 0).render(20).some(line => line.includes('fixture')) || typeof EditView !== 'function') {
    throw new Error('unexpected public exports');
  }
  console.log('PACKED_ENTRY_LOADED');
}
''')
    install = root / 'install'
    install.mkdir()
    agent = root / 'agent'
    agent.mkdir()
    env = dict(PATH=os.environ['PATH'], HOME=directory, TERM='xterm-256color', PI_CODING_AGENT_DIR=str(agent),
               PI_TELEMETRY='0', npm_config_cache=str(root / 'npm-cache'))
    packed = json.loads(run([npm, 'pack', '--json', '--pack-destination', directory], source, env))[0]
    assert {file['path'] for file in packed['files']} == {'package.json', 'dist/index.js'}, packed
    run([npm, 'install', '--legacy-peer-deps', '--ignore-scripts', '--no-audit', '--no-fund',
         '--fetch-retries=0', '--fetch-timeout=12000',
         str(root / packed['filename'])], install, env)
    modules = install / 'node_modules'
    assert not list(modules.rglob('@earendil-works/pi-*/package.json')), '安装树含第二套 Pi runtime'
    package = modules / manifest['name']
    assert json.loads((modules / '@jackice/pi-ui/package.json').read_text())['version'] == '0.4.2'
    (agent / 'settings.json').write_text(json.dumps({'packages': [str(package)]}))
    output = run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--list-models', 'pi-tool-ui-nonexistent'], root, env)
    assert 'PACKED_ENTRY_LOADED' in output, output
    print('干净安装：Pi 通过 package.json 的 pi.extensions 加载 dist/index.js；宿主 SDK 与 pi-ui@0.4.2 均可用')
