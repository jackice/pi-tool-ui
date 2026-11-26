import json
import os
from pathlib import Path
import subprocess
import tempfile

from screen import render
from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
provider = repo / 'tests/pty/bash-cases-provider.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-bashcfg-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text(json.dumps({
        'packages': [str(repo)],
        'toolUi': {'enabled': True, 'tools': {'bash': {
            'enabled': True,
            'showDuration': False,
            'showCwd': True,
            'output': {'previewRows': 3, 'ansi': False, 'showTruncation': False, 'showFullOutputPath': False},
        }}},
    }))
    observed = {}
    for case in ('ansi_rows', 'lines'):
        log = root / f'{case}.jsonl'
        env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
                   PI_CODING_AGENT_DIR=str(agent), PI_BASH_CASE=case,
                   PI_TOOL_UI_PROBE_LOG=str(log), PI_TOOL_UI_PROBE_RENDER='0')
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                              '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'bash',
                              'Run the local bash'], env, root, b'BASH_DONE', b'BASH_DONE', rows=60)
        observed[case] = {'screen': screen, 'text': '\n'.join(render(screen))}

    ansi = observed['ansi_rows']
    assert 'ms' not in ansi['text'], ansi['text']
    assert 'bashcfg' in ansi['text'], ansi['text']
    assert 'row 18' in ansi['text'] and 'row 17' not in ansi['text'] and 'row 20' in ansi['text'], ansi['text']
    assert b'\x1b[31m' not in ansi['screen'], 'ansi=false 仍输出颜色'
    lines = observed['lines']
    assert 'output truncated:' not in lines['text'], lines['text'][-400:]
    assert lines['text'].count('Full output:') == 1, lines['text'][-400:]
    evidence = repo / 'docs/evidence/bash-config.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'showDuration_false': True,
        'showCwd_true': True,
        'previewRows_3': True,
        'ansi_false': True,
        'showTruncation_false': True,
        'showFullOutputPath_false': True,
    }, ensure_ascii=False, indent=2) + '\n')
    print('Bash 配置 PTY：耗时/cwd/预览行/ANSI/截断/路径开关全部生效')
