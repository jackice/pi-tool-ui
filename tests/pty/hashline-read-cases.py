import json
import os
from pathlib import Path
import base64
import shutil
import subprocess
import tempfile

from terminal import capture_tui


pi = shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
workspace = Path(__file__).resolve().parents[3]
hashline = Path.home() / '.pi/agent/npm/node_modules/@jackice/hashline'
provider = Path(__file__).with_name('read-cases-provider.ts').resolve()

with tempfile.TemporaryDirectory(prefix='pi-tool-ui-read-') as directory:
    root = Path(directory)
    agent = root / 'agent'
    shutil.copytree(hashline, agent / 'extensions/hashline')
    for native in ('pi-utils', 'pi-natives', 'pi-natives-darwin-arm64'):
        shutil.copytree(Path.home() / f'.pi/agent/npm/node_modules/@oh-my-pi/{native}',
                        agent / f'node_modules/@oh-my-pi/{native}')
    (root / 'long.txt').write_text(''.join(f'line {number}\n' for number in range(1, 2101)))
    (root / 'pixel.png').write_bytes(base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='))
    log = root / 'events.jsonl'
    base_env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color',
                    PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0', PI_TOOL_UI_PROBE_LOG=str(log))
    base = [pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
            '-e', str(provider), '--model', 'tool-ui-probe/local',
            '--tools', 'read', 'Run the local read']
    observed = {}
    for case in ('range', 'missing', 'truncated', 'image'):
        log.unlink(missing_ok=True)
        capture_tui(base, dict(base_env, PI_TOOL_UI_READ_CASE=case), root, b'READ_CASE_DONE', b'READ_CASE_RENDER')
        events = [json.loads(line) for line in log.read_text().splitlines()]
        final = next(item for item in events if item['event'] == 'result')
        observed[case] = {'text': final['content'][0].get('text', ''), 'content': final['content'],
                          'details': final.get('details'), 'error': final['error']}

    ranged = observed['range']
    assert not ranged['error'] and ranged['text'].startswith('[long.txt#'), ranged
    assert '\n5:line 5\n6:line 6\n7:line 7\n' in ranged['text'], ranged
    missing = observed['missing']
    assert missing['error'] and '#' not in missing['text'].split('\n')[0], missing
    truncated = observed['truncated']
    assert not truncated['error'] and truncated['text'].startswith('[long.txt#'), truncated
    assert isinstance(truncated['details'], dict) and 'truncation' in truncated['details'], truncated
    lines = truncated['text'].splitlines()
    summary = {
        'text_lines': len(lines),
        'has_native_notice': any('Showing lines' in line for line in lines),
        'tail': lines[-4:],
        'details_keys': sorted(truncated['details']),
    }
    image = observed['image']
    kinds = [block['type'] for block in image['content']]
    assert 'image' in kinds and not image['text'].startswith('[pixel.png#'), image

    saved = [item for item in base if item != '--no-session'] + ['--session', str(root / 'history.jsonl')]
    subprocess.run([*saved, '--print'], cwd=root, env=dict(base_env, PI_TOOL_UI_READ_CASE='range'),
                   capture_output=True, text=True, timeout=40, check=True)
    log.unlink()
    capture_tui(saved, dict(base_env, PI_TOOL_UI_READ_CASE='range'), root, b'READ_CASE_RENDER', b'READ_CASE_RENDER')
    replayed = next(json.loads(line) for line in log.read_text().splitlines() if json.loads(line)['event'] == 'result')
    assert replayed['content'][0]['text'] == ranged['text'], replayed
    summary['image_kinds'] = kinds
    summary['history_replayed'] = True

    evidence = workspace / 'pi-tool-ui/docs/evidence/hashline-read-cases.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({'range': ranged, 'missing': missing, 'truncated': truncated, 'image': image, 'truncated_summary': summary},
                                   ensure_ascii=False, indent=2) + '\n')
    print(f"Hashline Read：范围编号、错误跳过、截断元数据、图片保留与历史回放均通过；原生截断提示={summary['has_native_notice']}")
