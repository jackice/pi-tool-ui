import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';

export default function (pi: ExtensionAPI) {
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('write', { path: 'export.txt', content: 'export-alpha\nexport-beta\n' }, { id: 'export-write' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage(fauxToolCall('read', { path: 'export.txt' }, { id: 'export-read' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('EXPORT_DONE'),
  ]);
  pi.registerProvider(faux.provider);
}
