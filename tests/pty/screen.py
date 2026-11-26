import re
from pathlib import Path

import pyte


def render(output, columns=100, lines=40):
    screen = pyte.Screen(columns, lines)
    stream = pyte.Stream(screen)
    stream.feed(output.decode(errors='replace'))
    return [line.rstrip() for line in screen.display]


def extract_card(output, root):
    frame = [line.replace(str(root), '<ROOT>').replace(str(Path(root).resolve()), '<ROOT>') for line in render(output)]
    start = max(index for index, line in enumerate(frame) if '╭─' in line)
    end = next(index for index in range(start, len(frame)) if frame[index].lstrip().startswith('╰'))
    card = [re.sub(r'· \d+(?:\.\d+)?m?s', '· <MS>', line) for line in frame[start:end + 1]]
    return [re.sub(r'─+', '─', line) if line.startswith(('╭', '╰')) else line for line in card]
