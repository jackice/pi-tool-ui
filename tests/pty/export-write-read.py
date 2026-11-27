import base64
import html as html_lib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from terminal import export_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/export-write-read-provider.ts'


def rendered_tools(html_path):
    html = html_path.read_text()
    match = re.search(r'<script id="session-data" type="application/json">([^<]+)</script>', html)
    assert match, '导出 HTML 缺少 session-data'
    data = json.loads(base64.b64decode(match.group(1)))
    return data.get('renderedTools'), data


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-export-wr-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'write': {'enabled': True}, 'read': {'enabled': True}}},
    }))
    session = root / 'session.jsonl'
    html = root / 'session.html'
    env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color',
               PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0')
    export_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'write,read',
                'Run the local export'], env, root, b'EXPORT_DONE', str(html))
    tools, data = rendered_tools(html)
    entries = json.dumps(data.get('entries'), ensure_ascii=False)
    assert 'export-alpha' in entries and 'export-beta' in entries, entries[-1000:]
    assert not tools, tools
    evidence = repo / 'docs/evidence/export-write-read.json'
    evidence.write_text(json.dumps({'pi_version': version, 'template_tools': True, 'custom_pre_rendered': False,
                                    'content_preserved': True},
                                   ensure_ascii=False, indent=2) + '\n')
    print('Write/Read /export：模板工具走宿主 HTML，正文保留，无自定义预渲染')
