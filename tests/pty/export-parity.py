import base64
import html as html_lib
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
        (root / 'notes.txt').write_text('alpha\nbeta\ngamma\n')
        log = root / f'{name}.jsonl'
        html = root / f'{name}.html'
        env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color',
                   PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0', PI_TOOL_UI_PROBE_LOG=str(log))
        export_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(root / f'{name}.session.jsonl'),
                    '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'read,hashline',
                    'Run the local edit'], env, root, b'BASELINE_HASHLINE_DONE', str(html))
        outputs[name] = rendered_tools(html)

    fields = ('callHtml', 'resultHtmlCollapsed', 'resultHtmlExpanded')
    ids = {}
    for name, tools in outputs.items():
        assert len(tools) == 1, tools
        tool_id, value = next(iter(tools.items()))
        assert isinstance(value, dict), value
        assert 'resultHtmlExpanded' in value, (name, tool_id, sorted(value))
        entry = {field: re.sub(r'· \d+(?:\.\d+)?m?s', '· <MS>', value[field]) if field in value else None
                 for field in fields}
        collapsed = html_lib.unescape(re.sub(r'<[^>]+>', '', entry['resultHtmlCollapsed'] or ''))
        expanded = html_lib.unescape(re.sub(r'<[^>]+>', '', entry['resultHtmlExpanded'] or ''))
        assert 'beta2' in expanded, expanded[-400:]
        ids[name] = entry
    assert ids['old'] == ids['new'], '旧扩展与新包的 call/collapsed/expanded HTML 不同'
    evidence = repo / 'docs/evidence/export-parity.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({'tools': 1, 'collapsed_empty': collapsed == '', 'diff_body_expanded': True, 'equal': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('Hashline TUI /export：旧新预渲染 HTML 一致；展开 Diff 正文存在')
