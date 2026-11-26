import pyte


def render(output, columns=100, lines=40):
    screen = pyte.Screen(columns, lines)
    stream = pyte.Stream(screen)
    stream.feed(output.decode(errors='replace'))
    return [line.rstrip() for line in screen.display]
