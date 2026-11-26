import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { Text } from '@earendil-works/pi-tui';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

const cases: Record<string, string> = {
  success: "printf 'ok\\n'",
  error: "sh -c 'exit 3'",
  lines: 'seq 1 2100',
};

export default function (pi: ExtensionAPI) {
  const name = process.env.PI_SLOT_CASE;
  const command = name === undefined ? undefined : cases[name];
  if (!command) throw new Error('未知的 PI_SLOT_CASE');
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const log = (event: string, data: object = {}) => appendFileSync(logPath, JSON.stringify({ event, ...data }) + '\n');
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('bash', { command }, { id: `slot-c-${name}` }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('SLOT_C_DONE'),
  ]);
  pi.registerProvider(faux.provider);
  pi.registerToolRenderer((tool, next) => {
    const original = next();
    if (tool !== 'bash' || !original) return original;
    return {
      ...original,
      renderResult(result, options, _theme, context) {
        const text = result.content.filter((block) => block.type === 'text').map((block) => block.text).join('\n');
        log('result', { partial: options.isPartial, shell: original.renderShell ?? 'default', pad: context.outputPad, error: context.isError, text: text.slice(0, 400), tail: text.slice(-200) });
        return new Text(`CUSTOM_OUT\n${text}`, 0, 0);
      },
    };
  });
}
