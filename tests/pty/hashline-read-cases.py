import json
import os
from pathlib import Path
import shutil
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
    log = root / 'events.jsonl'
    base_env = dict(PATH=os.environ['PATH'], HOME=str(root), TERM='xterm-256color',
                    PI_CODING_AGENT_DIR=str(agent), PI_TELEMETRY='0', PI_TOOL_UI_PROBE_LOG=str(log))
    base = [pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session',
            '-e', str(provider), '--model', 'tool-ui-probe/local',
            '--tools', 'read', 'Run the local read']
    observed = {}
    for case in ('range', 'missing', 'truncated'):
        log.unlink(missing_ok=True)
        capture_tui(base, dict(base_env, PI_TOOL_UI_READ_CASE=case), root, b'READ_CASE_DONE', b'READ_CASE_RENDER')
        events = [json.loads(line) for line in log.read_text().splitlines()]
        final = next(item for item in events if item['event'] == 'result')
        text = final['content'][0]['text']
        observed[case] = {'text': text, 'details': final.get('details'), 'error': final['error']}

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
    evidence = workspace / 'pi-tool-ui/docs/evidence/hashline-read-cases.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({'range': ranged, 'missing': missing, 'truncated': truncated, 'truncated_summary': summary},
                                   ensure_ascii=False, indent=2) + '\n')
    print(f"Hashline Read：范围编号、错误跳过改写、锚点与 details.truncation 共存；改写后正文含原生截断提示={summary['has_native_notice']}")
