import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { Text } from '@earendil-works/pi-tui';

export default function (pi: ExtensionAPI) {
  pi.registerToolRenderer((name, next) => {
    const original = next();
    if (name !== 'bash' || !original) return original;
    return { ...original, renderResult: () => new Text('PEER_BASH', 0, 0) };
  });
}
