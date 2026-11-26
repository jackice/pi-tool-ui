import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { Text } from '@earendil-works/pi-tui';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

export default function (pi: ExtensionAPI) {
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const log = (event: string, data: object = {}) => appendFileSync(logPath, JSON.stringify({ event, ...data }) + '\n');
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('bash', { command: "printf 'ok\\n'" }, { id: 'slot-c' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('SLOT_C_DONE'),
  ]);
  pi.registerProvider(faux.provider);
  pi.registerToolRenderer((tool, next) => {
    const original = next();
    if (tool !== 'bash' || !original) return original;
    return {
      ...original,
      renderResult(_result, options, _theme, context) {
        log('result', { partial: options.isPartial, shell: original.renderShell ?? 'default' });
        return new Text('CUSTOM_OUT', 0, 0);
      },
    };
  });
}
