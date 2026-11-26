import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { Text } from '@earendil-works/pi-tui';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

const cases: Record<string, { path: string; offset?: number; limit?: number }> = {
  range: { path: 'long.txt', offset: 5, limit: 3 },
  missing: { path: 'missing.txt' },
  truncated: { path: 'long.txt' },
  image: { path: 'pixel.png' },
};

export default function (pi: ExtensionAPI) {
  const name = process.env.PI_TOOL_UI_READ_CASE;
  const entry = name === undefined ? undefined : cases[name];
  if (!entry) throw new Error('未知的 PI_TOOL_UI_READ_CASE');
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('read', entry, { id: `case-${name}` }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('READ_CASE_DONE'),
  ]);
  pi.registerProvider(faux.provider);
  pi.registerToolRenderer((tool, next) => {
    const original = next();
    if (tool !== 'read' || !original) return original;
    return {
      ...original,
      renderResult(result, options, _theme, context) {
        if (!options.isPartial) appendFileSync(logPath, JSON.stringify({
          event: 'result', error: context.isError, content: result.content, details: result.details,
        }) + '\n');
        return new Text('READ_CASE_RENDER', 0, 0);
      },
    };
  });
}
