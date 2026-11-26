import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';

export default function (pi: ExtensionAPI) {
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('edit', { path: 'notes.txt', oldText: 'missing', newText: 'x' }, { id: 'error-edit' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('BASELINE_DONE'),
  ]);
  pi.registerProvider(faux.provider);
}
