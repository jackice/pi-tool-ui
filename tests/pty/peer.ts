import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { Text } from '@earendil-works/pi-tui';
import { appendFileSync } from 'node:fs';

export default function (pi: ExtensionAPI) {
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  pi.registerToolRenderer((name, next) => {
    if (name === 'read') appendFileSync(logPath, '{"event":"peer-enter"}\n');
    const original = next();
    if (name !== 'read' || !original) return original;
    appendFileSync(logPath, JSON.stringify({ event: 'peer-return', shell: original.renderShell }) + '\n');
    return { ...original, renderShell: 'self', renderResult: () => new Text('PEER_RESULT', 0, 0) };
  });
}
