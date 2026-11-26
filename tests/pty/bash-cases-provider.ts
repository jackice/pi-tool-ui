import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { Text } from '@earendil-works/pi-tui';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

const cases: Record<string, string> = {
  success: "printf 'ok\\n'",
  empty: 'true',
  nonzero: 'false',
  lines: 'seq 1 2100',
  bytes: "for i in $(seq 1 1500); do printf 'line%04d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\\n' \"$i\"; done",
  longline: "printf 'a%.0s' {1..60000}",
  risky: "sh -c 'echo run >> count.txt'",
  risky_abort: "sh -c 'seq 1 3000; sleep 5; echo run >> count.txt'",
  risky_slow: "sh -c 'sleep 5; echo run >> count.txt'",
  trunc_timeout: 'seq 1 2100; sleep 5',
  count: 'echo run >> count.txt',
  count_compress: 'echo run >> count.txt; for i in $(seq 1 100); do echo same-line; done',
  write: "printf 'ok\\n' > out.txt",
  compress: 'for i in $(seq 1 500); do echo same-line; done',
  stream: "printf 'first\\n'; sleep 0.4; printf 'second\\n'",
};

export default function (pi: ExtensionAPI) {
  const name = process.env.PI_BASH_CASE;
  const command = name === undefined ? undefined : cases[name];
  if (!command) throw new Error('未知的 PI_BASH_CASE');
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  const timeout = Number(process.env.PI_BASH_TIMEOUT ?? '0');
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('bash', { command, ...(timeout > 0 ? { timeout } : {}) }, { id: `bash-${name}` }), { stopReason: 'toolUse' }),
    (context: unknown) => {
      const messages = (context as { messages?: { role?: string; content?: unknown }[] }).messages ?? [];
      const last = messages.filter((message) => message.role === 'toolResult').at(-1);
      const blocks = Array.isArray(last?.content) ? last.content as { type?: string; text?: string }[] : [];
      const text = blocks.filter((block) => block.type === 'text').map((block) => block.text ?? '').join('\n');
      appendFileSync(logPath, JSON.stringify({ event: 'model', text }) + '\n');
      return fauxAssistantMessage('BASH_DONE');
    },
  ]);
  pi.registerProvider(faux.provider);
  pi.on('tool_call', (event) => {
    if (event.toolName === 'bash') appendFileSync(logPath, '{"event":"tool-execution"}\n');
  });
  if (process.env.PI_TOOL_UI_PROBE_RENDER === 'log') pi.registerToolRenderer((tool, next) => {
    const original = next();
    if (tool !== 'bash' || !original) return original;
    return {
      ...original,
      renderResult(result, options, theme, context) {
        appendFileSync(logPath, JSON.stringify({ event: 'result', partial: options.isPartial, error: context.isError, durationMs: context.durationMs, args: context.args, content: result.content, details: result.details }) + '\n');
        return original.renderResult!(result, options, theme, context);
      },
    };
  });
  if (process.env.PI_TOOL_UI_PROBE_RENDER !== '0' && process.env.PI_TOOL_UI_PROBE_RENDER !== 'log') pi.registerToolRenderer((tool, next) => {
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
