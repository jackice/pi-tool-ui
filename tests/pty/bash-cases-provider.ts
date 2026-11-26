import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { Text } from '@earendil-works/pi-tui';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

const cases: Record<string, string> = {
  success: "printf 'ok\\n'",
  empty: 'true',
  nonzero: 'false',
  lines: 'seq 1 2100',
  bytes: "yes x | head -c 60000",
  longline: "printf 'a%.0s' {1..60000}",
  stream: "printf 'first\\n'; sleep 0.4; printf 'second\\n'",
};

export default function (pi: ExtensionAPI) {
  const name = process.env.PI_BASH_CASE;
  const command = name === undefined ? undefined : cases[name];
  if (!command) throw new Error('未知的 PI_BASH_CASE');
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('bash', { command }, { id: `bash-${name}` }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('BASH_DONE'),
  ]);
  pi.registerProvider(faux.provider);
  pi.registerToolRenderer((tool, next) => {
    const original = next();
    if (tool !== 'bash' || !original) return original;
    return {
      ...original,
      renderResult(result, options, _theme, context) {
        appendFileSync(logPath, JSON.stringify({
          event: 'result', partial: options.isPartial, error: context.isError,
          durationMs: context.durationMs, args: context.args, content: result.content, details: result.details,
        }) + '\n');
        return new Text('BASH_PROBE', 0, 0);
      },
    };
  });
}
