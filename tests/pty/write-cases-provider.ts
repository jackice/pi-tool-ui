import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { Text } from '@earendil-works/pi-tui';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

const cases: Record<string, { path: string; content: string }> = {
  success: { path: 'out.txt', content: 'alpha\nbeta\n' },
  empty: { path: 'empty.txt', content: '' },
  unicode: { path: 'unicode.txt', content: '中文🙂\nno trailing newline' },
  overwrite: { path: 'out.txt', content: 'replaced\n' },
  many: { path: 'many.txt', content: Array.from({ length: 20 }, (_, index) => `line ${index + 1}`).join('\n') },
  error: { path: 'dir', content: 'x' },
  code: { path: 'out.ts', content: 'const value = 1;\nexport default value;\n' },
};

export default function (pi: ExtensionAPI) {
  const name = process.env.PI_WRITE_CASE;
  const target = name === undefined ? undefined : cases[name];
  if (!target) throw new Error('未知的 PI_WRITE_CASE');
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const stream = process.env.PI_WRITE_STREAM === '1';
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }], ...(stream ? { tokensPerSecond: 30, tokenSize: { min: 1, max: 2 } } : {}) });
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('write', target, { id: `write-${name}` }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('WRITE_DONE'),
  ]);
  pi.registerProvider(faux.provider);
  pi.on('tool_call', (event) => {
    if (event.toolName === 'write') appendFileSync(logPath, '{"event":"tool-execution"}\n');
  });
  if (process.env.PI_TOOL_UI_PROBE_RENDER !== '0') pi.registerToolRenderer((tool, next) => {
    const original = next();
    if (tool !== 'write' || !original) return original;
    return {
      ...original,
      renderCall(args, _theme, context) {
        appendFileSync(logPath, JSON.stringify({ event: 'call', args, argsComplete: context.argsComplete }) + '\n');
        if (original.renderCall) return original.renderCall(args, _theme, context);
        return new Text('WRITE_CALL', 0, 0);
      },
      renderResult(result, options, _theme, context) {
        appendFileSync(logPath, JSON.stringify({
          event: 'result', partial: options.isPartial, error: context.isError,
          args: context.args, content: result.content, details: result.details,
        }) + '\n');
        return new Text('WRITE_PROBE', 0, 0);
      },
    };
  });
}
