import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { fauxProvider, fauxAssistantMessage, fauxToolCall, type TranscriptContext } from '@earendil-works/pi-ai';

export default function (pi: ExtensionAPI) {
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  const patch = (context: TranscriptContext) => {
    const match = /\[notes\.txt#([0-9a-fA-F]+)\]/.exec(JSON.stringify(context));
    if (!match) throw new Error('缺少 noop 锚点');
    return `[notes.txt#${match[1]}]\nPUT 2.=2:\n+beta`;
  };
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('read', { path: 'notes.txt' }, { id: 'noop-read' }), { stopReason: 'toolUse' }),
    (context) => fauxAssistantMessage(
      fauxToolCall('hashline', { input: patch(context) }, { id: 'noop-hashline' }),
      { stopReason: 'toolUse' },
    ),
    fauxAssistantMessage('NOOP_DONE'),
  ]);
  pi.registerProvider(faux.provider);
}
