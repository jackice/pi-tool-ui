import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

export default function (pi: ExtensionAPI) {
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('write', { path: 'out.txt', content: 'alpha\nbeta\n' }, { id: 'integration-write' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage(fauxToolCall('read', { path: 'out.txt' }, { id: 'integration-read' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage(fauxToolCall('bash', { command: 'printf integration-bash' }, { id: 'integration-bash' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('INTEGRATION_DONE'),
  ]);
  pi.registerProvider(faux.provider);
  pi.on('tool_call', (event) => {
    appendFileSync(logPath, JSON.stringify({ event: 'execute', tool: event.toolName }) + '\n');
  });
}
