import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

export default function (pi: ExtensionAPI) {
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const log = (event: string) => appendFileSync(logPath, JSON.stringify({ event }) + '\n');
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  faux.setResponses([
    fauxAssistantMessage(
      fauxToolCall('edit', { path: 'notes.txt', oldText: 'beta', newText: 'beta2' }, { id: 'baseline-edit' }),
      { stopReason: 'toolUse' },
    ),
    fauxAssistantMessage('BASELINE_DONE'),
  ]);
  pi.registerProvider(faux.provider);
  pi.on('tool_call', (event) => { if (event.toolName === 'edit') log('tool-execution'); });
}
