import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { Text } from '@earendil-works/pi-tui';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

const stateKey = Symbol('bash-slot-b');

export default function (pi: ExtensionAPI) {
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const log = (event: string, data: object = {}) => appendFileSync(logPath, JSON.stringify({ event, ...data }) + '\n');
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('bash', { command: "printf 'first\\n'; sleep 0.4; printf 'second\\n'" }, { id: 'slot-b' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('SLOT_DONE'),
  ]);
  pi.registerProvider(faux.provider);
  pi.registerToolRenderer((tool, next) => {
    const original = next();
    if (tool !== 'bash' || !original) return original;
    return {
      ...original,
      renderShell: 'self',
      renderCall(_args, theme, context) {
        (context.state[stateKey] ??= { calls: 0 }) as { calls: number };
        log('call', { pad: context.outputPad });
        return new Text(theme.fg('muted', 'BASH_TOP\n╭─ Bash ─╮\n│ $ command │'), 0, 0);
      },
      renderResult(_result, options, _theme, context) {
        const state = context.state[stateKey] as { calls: number } | undefined;
        log('result', { partial: options.isPartial, shared: state !== undefined });
        return new Text('│ output │\nBASH_BOTTOM\n╰─────────╯', 0, 0);
      },
    };
  });
}
