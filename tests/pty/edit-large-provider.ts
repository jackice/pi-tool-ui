import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';

const lines = Array.from({ length: 40 }, (_, index) => `line ${index + 1}`);
const oldText = `${lines.join('\n')}\n`;
const newText = `${lines.map((line) => `${line} changed`).join('\n')}\n`;

export default function (pi: ExtensionAPI) {
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('edit', { path: 'notes.txt', oldText, newText }, { id: 'large-edit' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('BASELINE_DONE'),
  ]);
  pi.registerProvider(faux.provider);
}
