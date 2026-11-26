import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { fauxProvider, fauxAssistantMessage, fauxToolCall, type TranscriptContext } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

export default function (pi: ExtensionAPI) {
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const log = (event: string) => appendFileSync(logPath, JSON.stringify({ event }) + '\n');
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  const patch = (context: TranscriptContext) => {
    const text = JSON.stringify(context);
    const match = /\[notes\.txt#([0-9a-fA-F]+)\]/.exec(text);
    if (!match) throw new Error('read 结果中缺少 Hashline 锚点');
    return `[notes.txt#${match[1]}]\nPUT 2.=2:\n+beta2`;
  };
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('read', { path: 'notes.txt' }, { id: 'baseline-read' }), { stopReason: 'toolUse' }),
    (context) => fauxAssistantMessage(
      fauxToolCall('hashline', { input: patch(context) }, { id: 'baseline-hashline' }),
      { stopReason: 'toolUse' },
    ),
    fauxAssistantMessage('BASELINE_HASHLINE_DONE'),
  ]);
  pi.registerProvider(faux.provider);
  pi.on('tool_call', (event) => { if (event.toolName === 'hashline') log('tool-execution'); });
}
