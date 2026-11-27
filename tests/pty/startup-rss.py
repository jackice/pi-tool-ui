import json
import os
from pathlib import Path
import pty
import select
import shutil
import subprocess
import tempfile
import time

import fcntl
import struct
import termios


pi = os.environ.get('PI_BIN') or shutil.which('pi')
assert pi, '需要 Pi 1.6.0'
version = subprocess.run([pi, '--version'], capture_output=True, text=True, check=True).stdout.strip()
assert version == '1.6.0', version
workspace = Path(__file__).resolve().parents[3]
repo = workspace / 'pi-tool-ui'
subprocess.run(['npm', 'run', 'build'], cwd=repo, check=True, capture_output=True, text=True)


def median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 == 1 else (ordered[middle - 1] + ordered[middle]) / 2


def measure(root, enabled, package_path):
    work = root / ('on' if enabled else 'off')
    if not work.exists():
        work.mkdir()
        agent = work / 'agent'
        agent.mkdir()
        (agent / 'settings.json').write_text(json.dumps({
            'packages': [str(package_path)] if enabled else [],
            'toolUi': {'enabled': enabled, 'tools': {
                'bash': {'enabled': enabled}, 'write': {'enabled': enabled}, 'read': {'enabled': enabled},
            }},
        }))
    agent = work / 'agent'
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
    env = dict(PATH=os.environ['PATH'], HOME=str(work), TERM='xterm-256color', PI_TELEMETRY='0',
               PI_CODING_AGENT_DIR=str(agent))
    start = time.perf_counter()
    process = subprocess.Popen([pi, '--offline', '--no-approve', '--no-mcp', '-nc', '--no-session'],
                               stdin=slave, stdout=slave, stderr=slave, cwd=work, env=env)
    os.close(slave)
    output = bytearray()
    ready_ms = None
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.02)[0]:
                output.extend(os.read(master, 65536))
                if b'Press ctrl+o' in output:
                    ready_ms = (time.perf_counter() - start) * 1000
                    break
        assert ready_ms is not None, output[-2000:].decode(errors='replace')
        time.sleep(0.5)
        while select.select([master], [], [], 0)[0]:
            output.extend(os.read(master, 65536))
        rss_kb = int(subprocess.run(['ps', '-o', 'rss=', '-p', str(process.pid)], capture_output=True, text=True,
                                    check=True).stdout.strip())
        return {'startup_ms': ready_ms, 'rss_kb': rss_kb}
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        os.close(master)


with tempfile.TemporaryDirectory(prefix='pi-tool-ui-t7perf-') as directory:
    root = Path(directory)
    npm = shutil.which('npm')
    assert npm, '需要 npm'
    env = dict(PATH=os.environ['PATH'], HOME=directory, npm_config_cache=str(root / 'npm-cache'), TERM='xterm-256color')
    packed = json.loads(subprocess.run([npm, 'pack', '--json', '--pack-destination', directory], cwd=repo, env=env, capture_output=True, text=True, check=True).stdout)[0]
    ui_packed = json.loads(subprocess.run([npm, 'pack', '--json', '--pack-destination', directory], cwd=repo.parent / 'pi-ui', env=env, capture_output=True, text=True, check=True).stdout)[0]
    install = root / 'install'
    install.mkdir()
    subprocess.run([npm, 'install', '--legacy-peer-deps', '--ignore-scripts', '--no-audit', '--no-fund', '--fetch-retries=0', '--fetch-timeout=20000', str(root / packed['filename']), str(root / ui_packed['filename'])], cwd=install, env=env, capture_output=True, text=True, check=True)
    package_path = install / 'node_modules/@jackice/pi-tool-ui'
    assert (package_path / 'dist/index.js').is_file()
    samples = {'off': [], 'on': []}
    for index in range(20):
        order = ('off', 'on') if index % 2 == 0 else ('on', 'off')
        for name in order:
            samples[name].append(measure(root, name == 'on', package_path))
    report = {}
    for name in ('off', 'on'):
        report[name] = {
            'startup_ms': median([item['startup_ms'] for item in samples[name]]),
            'rss_mib': median([item['rss_kb'] for item in samples[name]]) / 1024,
            'samples': len(samples[name]),
        }
    report['startup_delta_ms'] = report['on']['startup_ms'] - report['off']['startup_ms']
    report['rss_delta_mib'] = report['on']['rss_mib'] - report['off']['rss_mib']
    report['pi_version'] = version
    report['budget'] = {'startup_delta_ms': 20, 'rss_delta_mib': 5}
    report['passed'] = report['startup_delta_ms'] <= 20 and report['rss_delta_mib'] <= 5
    evidence = repo / 'docs/evidence/startup-rss.json'
    evidence.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f"启动/RSS：OFF {report['off']['startup_ms']:.1f}ms/{report['off']['rss_mib']:.1f}MiB "
          f"ON {report['on']['startup_ms']:.1f}ms/{report['on']['rss_mib']:.1f}MiB "
          f"delta {report['startup_delta_ms']:.1f}ms/{report['rss_delta_mib']:.2f}MiB passed={report['passed']}")
    assert report['passed']
