import base64
import json
import os
from pathlib import Path
import shutil
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
provider = repo / 'tests/pty/read-cases-provider.ts'
hashline = Path.home() / '.pi/agent/npm/node_modules/@jackice/hashline'
assert hashline.exists(), '缺少 @jackice/hashline 0.1.2'

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-rhash-ab-') as directory:
    root = Path(directory)
    (root / 'long.txt').write_text(''.join(f'line {number}\n' for number in range(1, 2101)))
    (root / 'pixel.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='))
    observed = {}
    for case in ('range', 'truncated'):
        for enabled in (False, True):
            work = root / f'{case}-{"on" if enabled else "off"}'
            work.mkdir()
            for name in ('long.txt', 'pixel.png'):
                shutil.copyfile(root / name, work / name)
            agent = work / 'agent'
            shutil.copytree(hashline, agent / 'extensions/hashline')
            for native in ('pi-utils', 'pi-natives', 'pi-natives-darwin-arm64'):
                shutil.copytree(Path.home() / f'.pi/agent/npm/node_modules/@oh-my-pi/{native}', agent / f'node_modules/@oh-my-pi/{native}')
            settings = {'packages': [str(repo)], 'toolUi': {'enabled': enabled, 'tools': {'read': {'enabled': enabled}}}}
            (agent / 'settings.json').write_text(json.dumps(settings))
            log = work / 'events.jsonl'
            env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
                       PI_CODING_AGENT_DIR=str(agent), PI_TOOL_UI_READ_CASE=case,
                       PI_TOOL_UI_PROBE_LOG=str(log), PI_READ_CASE_PROBE_RENDER='0')
            session = work / 'session.jsonl'
            screen = capture_tui([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--session', str(session),
                                  '-e', str(provider), '--model', 'tool-ui-probe/local', '--tools', 'read',
                                  'Run the local read'], env, work, b'READ_CASE_DONE', b'READ_CASE_DONE', rows=60)
            events = [json.loads(line) for line in log.read_text().splitlines()]
            final = next(json.loads(line)['message'] for line in session.read_text().splitlines()
                         if json.loads(line).get('type') == 'message' and isinstance(json.loads(line).get('message'), dict)
                         and json.loads(line)['message'].get('role') == 'toolResult')
            observed[f'{case}-{"on" if enabled else "off"}'] = {
                'content': final['content'], 'details': final.get('details'), 'error': final.get('isError', False),
                'executions': sum(1 for item in events if item.get('event') == 'tool-execution'),
                'text': '\n'.join(render(screen, lines=60)),
            }

    for case in ('range', 'truncated'):
        on = observed[f'{case}-on']; off = observed[f'{case}-off']
        assert on['content'] == off['content'] and on['details'] == off['details'], case
        assert on['executions'] == off['executions'] == 1, case
        text = on['content'][0]['text']
        assert text.startswith('[long.txt#') and '5:line 5' in text, text[:200]
        assert 'Read' in on['text'], on['text'][-600:]
        assert 'Read' not in off['text'], off['text'][-600:]
    evidence = repo / 'docs/evidence/read-hashline-ab.json'
    evidence.write_text(json.dumps({'pi_version': version, 'range_equal': True, 'truncated_equal': True,
                                    'runs': 1, 'anchors_preserved': True, 'card_on': True, 'card_off': False},
                                   ensure_ascii=False, indent=2) + '\n')
    print('Read Hashline A/B：range/truncated content/details 一致、各执行一次，锚点保留；ON 卡片、OFF 原生')
