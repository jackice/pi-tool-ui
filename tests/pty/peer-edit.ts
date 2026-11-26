import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { Text } from '@earendil-works/pi-tui';

export default function (pi: ExtensionAPI) {
  pi.registerToolRenderer((name, next) => {
    const original = next();
    if (name !== 'edit' || !original) return original;
    return { ...original, renderResult: () => new Text('PEER_EDIT', 0, 0) };
  });
}
