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
    fauxAssistantMessage(fauxToolCall('read', { path: 'fixture.txt' }, { id: 'probe-read' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('PROBE_DONE'),
  ]);
  pi.registerProvider(faux.provider);
  pi.on('session_start', (_, ctx) => { log('session', { hasUI: ctx.hasUI }); });
  const callComponent = Symbol('probe-call');
  const resultComponent = Symbol('probe-result');
  pi.registerToolRenderer((name, next) => {
    const original = next();
    if (name !== 'read' || !original) return original;
    log('resolve', { shell: original.renderShell });
    return {
      ...original,
      renderShell: 'self',
      renderCall(_args, _theme, ctx) {
        log('call', { id: ctx.toolCallId, pad: ctx.outputPad, reused: !!ctx.state[callComponent] && ctx.lastComponent === ctx.state[callComponent] });
        return ctx.state[callComponent] ??= new Text('PROBE_CALL', 0, 0);
      },
      renderResult(result, options, _theme, ctx) {
        log('result', {
          id: ctx.toolCallId, pad: ctx.outputPad, expanded: options.expanded, partial: options.isPartial,
          shared: !!ctx.state[callComponent], reused: !!ctx.state[resultComponent] && ctx.lastComponent === ctx.state[resultComponent],
          error: ctx.isError, content: result.content,
        });
        return ctx.state[resultComponent] ??= new Text('PROBE_RESULT', 0, 0);
      },
    };
  });
}
