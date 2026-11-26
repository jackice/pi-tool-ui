import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from terminal import capture_tui


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
probe = repo / 'tests/pty/bash-slot-c-probe.ts'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-slotc-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    agent.mkdir()
    (agent / 'settings.json').write_text('{}')
    observed = {}
    for case in ('success', 'error', 'lines'):
        log = root / f'{case}.jsonl'
        env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color', PI_TELEMETRY='0',
                   PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_PROBE_LOG=str(log), PI_SLOT_CASE=case)
        screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
                              '-e', str(probe), '--model', 'tool-ui-probe/local', '--tools', 'bash',
                              'Run the local bash'], env, root, b'SLOT_C_DONE', b'SLOT_C_DONE')
        events = [json.loads(line) for line in log.read_text().splitlines()]
        final = next(item for item in events if item['event'] == 'result' and not item['partial'])
        observed[case] = {'final': final, 'screen': screen}

    commands = {'success': b"printf 'ok", 'error': b'exit 3', 'lines': b'seq 1 2100'}
    for case, value in observed.items():
        final = value['final']
        assert final['shell'] == 'default' and final['pad'] == 1, final
        assert value['screen'].count(b'CUSTOM_OUT') == 1, case
        assert value['screen'].count(commands[case]) == 1, (case, value['screen'].count(commands[case]))
        assert final['text'], case
        if case == 'error':
            assert final['error'] is True
        if case == 'lines':
            assert b'Full output:' in value['screen'], value['screen'][-300:]

    evidence = repo / 'docs/evidence/bash-slot-c.json'
    evidence.write_text(json.dumps({
        'pi_version': version,
        'candidate': 'C',
        'native_shell_preserved': True,
        'command_once': True,
        'custom_output_once': True,
        'cases': {case: {'error': value['final']['error'], 'pad': value['final']['pad'],
                         'text_head': value['final']['text'][:120]} for case, value in observed.items()},
    }, ensure_ascii=False, indent=2) + '\n')
    print('Bash slot C：成功/错误/截断均保留原生 shell，命令一次，诊断文本进入 result')
