import base64
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from terminal import export_tui


pi = shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
old = workspace / 'dotfiles/pi/.pi/agent/extensions/hashline-diff'
hashline = Path.home() / '.pi/agent/npm/node_modules/@jackice/hashline'
library = old / 'node_modules/@jackice/pi-ui'
provider = repo / 'tests/pty/hashline-provider.ts'


def install_hashline(agent):
    shutil.copytree(hashline, agent / 'extensions/hashline')
    for native in ('pi-utils', 'pi-natives', 'pi-natives-darwin-arm64'):
        shutil.copytree(Path.home() / f'.pi/agent/npm/node_modules/@oh-my-pi/{native}',
                        agent / f'node_modules/@oh-my-pi/{native}')


def rendered_tools(html_path):
    html = html_path.read_text()
    match = re.search(r'<script id="session-data" type="application/json">([^<]+)</script>', html)
    assert match, '导出 HTML 缺少 session-data'
    data = json.loads(base64.b64decode(match.group(1)))
    tools = data.get('renderedTools')
    assert tools, '导出 HTML 未预渲染自定义工具'
    return tools


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-export-') as directory:
    root = Path(directory)
    (root / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
    agents = {}
    old_agent = root / 'old-agent'
    install_hashline(old_agent)
    shutil.copytree(old, old_agent / 'extensions/hashline-diff', ignore=shutil.ignore_patterns('node_modules'))
    (old_agent / 'extensions/hashline-diff/node_modules/@jackice').mkdir(parents=True)
    shutil.copytree(library, old_agent / 'extensions/hashline-diff/node_modules/@jackice/pi-ui')
    (old_agent / 'settings.json').write_text(json.dumps({'editDiff': {'nativeEdit': True}}))
    agents['old'] = old_agent

    new_agent = root / 'new-agent'
    install_hashline(new_agent)
    (new_agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'edit': {'enabled': True}, 'hashline': {'enabled': True}}},
    }))
    agents['new'] = new_agent

    outputs = {}
    for name, agent in agents.items():
        log = root / f'{name}.jsonl'
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
