import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

export default function (pi: ExtensionAPI) {
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const log = (event: string, data: object) => appendFileSync(logPath, JSON.stringify({ event, ...data }) + '\n');
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }], tokensPerSecond: 30, tokenSize: { min: 1, max: 2 } });
  if (process.env.PI_CONTEXT_PROVIDER === '1') {
    faux.setResponses([
      fauxAssistantMessage(fauxToolCall('write', { path: 'many.txt', content: Array.from({ length: 20 }, (_, index) => `line ${index + 1}`).join('\n') }, { id: 'ctx-write' }), { stopReason: 'toolUse' }),
      fauxAssistantMessage('CONTEXT_DONE'),
    ]);
  }
  pi.registerProvider(faux.provider);
  pi.registerToolRenderer((tool, next) => {
    const original = next();
    if (tool !== 'write' || !original) return original;
    return {
      ...original,
      renderCall(args, theme, context) {
        const record = args as Record<string, unknown>;
        log('call', {
          isPartial: context.isPartial, argsComplete: context.argsComplete,
          executionStarted: context.executionStarted, len: typeof record.content === 'string' ? record.content.length : -1,
          hasState: Object.keys(context.state).length, last: context.lastComponent?.constructor?.name ?? null,
        });
        return original.renderCall ? original.renderCall(args, theme, context) : { render: () => [], invalidate: () => {} };
      },
      renderResult(result, options, theme, context) {
        log('result', { isPartial: options.isPartial, argsComplete: context.argsComplete, executionStarted: context.executionStarted, error: context.isError });
        return original.renderResult ? original.renderResult(result, options, theme, context) : { render: () => [], invalidate: () => {} };
      },
    };
  });
}
