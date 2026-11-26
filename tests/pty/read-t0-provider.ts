import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { Text } from '@earendil-works/pi-tui';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

const cases: Record<string, { path: string; offset?: number; limit?: number }> = {
  basic: { path: 'short.txt' },
  range: { path: 'long.txt', offset: 5, limit: 3 },
  eof: { path: 'short.txt', offset: 99 },
  zero: { path: 'long.txt', limit: 0 },
  empty: { path: 'empty.txt' },
  notice: { path: 'notice.txt' },
  truncated: { path: 'long.txt' },
  longline: { path: 'longline.txt' },
};

export default function (pi: ExtensionAPI) {
  const name = process.env.PI_READ_CASE;
  const target = name === undefined ? undefined : cases[name];
  if (!target) throw new Error(`未知的 PI_READ_CASE=${String(name)}`);
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('read', target, { id: `read-${name}` }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('READ_T0_DONE'),
  ]);
  pi.registerProvider(faux.provider);
  pi.registerToolRenderer((tool, next) => {
    const original = next();
    if (tool !== 'read' || !original) return original;
    return {
      ...original,
      renderResult(result, options, _theme, context) {
        appendFileSync(logPath, JSON.stringify({
          event: 'result', partial: options.isPartial, error: context.isError,
          args: context.args, content: result.content, details: result.details,
        }) + '\n');
        return new Text('READ_T0_PROBE', 0, 0);
      },
    };
  });
}
