import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


pi = shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
old = workspace / 'dotfiles/pi/.pi/agent/extensions/hashline-diff'
hashline = Path.home() / '.pi/agent/npm/node_modules/@jackice/hashline'
library = old / 'node_modules/@jackice/pi-ui'
provider = repo / 'tests/pty/hashline-provider.ts'


def run(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def install_hashline(agent):
    shutil.copytree(hashline, agent / 'extensions/hashline')
    for native in ('pi-utils', 'pi-natives', 'pi-natives-darwin-arm64'):
        shutil.copytree(Path.home() / f'.pi/agent/npm/node_modules/@oh-my-pi/{native}',
                        agent / f'node_modules/@oh-my-pi/{native}')


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-export-') as directory:
    root = Path(directory)
    (root / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
    session_agent = root / 'session-agent'
    install_hashline(session_agent)
    shutil.copytree(old, session_agent / 'extensions/hashline-diff', ignore=shutil.ignore_patterns('node_modules'))
    (session_agent / 'extensions/hashline-diff/node_modules/@jackice').mkdir(parents=True)
    shutil.copytree(library, session_agent / 'extensions/hashline-diff/node_modules/@jackice/pi-ui')
    (session_agent / 'settings.json').write_text(json.dumps({'editDiff': {'nativeEdit': True}}))
    session = root / 'session.jsonl'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color',
               PI_CODING_AGENT_DIR=str(session_agent), PI_TELEMETRY='0',
               PI_TOOL_UI_PROBE_LOG=str(root / 'events.jsonl'))
    run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
         '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'read,hashline',
         '--print', 'Run the local edit'], root, env)
    assert session.is_file() and b'beta2' in session.read_bytes()

    agents = {'old': session_agent, 'new': root / 'new-agent'}
    install_hashline(agents['new'])
    (agents['new'] / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'edit': {'enabled': True}, 'hashline': {'enabled': True}}},
    }))
    outputs = {}
    for name, agent in agents.items():
        html = root / f'{name}.html'
        run([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--export', str(session), str(html)], root,
            dict(env, PI_CODING_AGENT_DIR=str(agent)))
        text = html.read_text()
        outputs[name] = re.sub(r'(session[-_ ]?id|timestamp)[^<]{0,80}', r'\1', text, flags=re.IGNORECASE)
    assert outputs['old'] == outputs['new'], '旧扩展与新包导出的 Hashline HTML 不同'
    body = {'old_has_diff_body': 'beta2' in outputs['old'], 'new_has_diff_body': 'beta2' in outputs['new']}
    assert body['old_has_diff_body'] == body['new_has_diff_body']
    evidence = repo / 'docs/evidence/export-parity.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(body, ensure_ascii=False, indent=2) + '\n')
    print(f"Hashline /export：旧新 HTML 一致；工具正文出现={body['old_has_diff_body']}（Pi 导出模板行为，两版相同）")
