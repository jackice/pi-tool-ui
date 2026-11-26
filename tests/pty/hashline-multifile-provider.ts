import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { fauxProvider, fauxAssistantMessage, fauxToolCall, type TranscriptContext } from '@earendil-works/pi-ai';
import { appendFileSync } from 'node:fs';

export default function (pi: ExtensionAPI) {
  const logPath = process.env.PI_TOOL_UI_PROBE_LOG;
  if (!logPath) throw new Error('PI_TOOL_UI_PROBE_LOG is required');
  const log = () => appendFileSync(logPath, '{"event":"tool-execution"}\n');
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  const patch = (context: TranscriptContext) => {
    const text = JSON.stringify(context);
    const a = /\[a\.txt#([0-9a-fA-F]+)\]/.exec(text);
    const b = /\[b\.txt#([0-9a-fA-F]+)\]/.exec(text);
    if (!a || !b) throw new Error('缺少多文件锚点');
    return `[a.txt#${a[1]}]\nPUT 1.=1:\n+alpha2\n[b.txt#${b[1]}]\nPUT 1.=1:\n+beta2`;
  };
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('read', { path: 'a.txt' }, { id: 'read-a' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage(fauxToolCall('read', { path: 'b.txt' }, { id: 'read-b' }), { stopReason: 'toolUse' }),
    (context) => fauxAssistantMessage(
      fauxToolCall('hashline', { input: patch(context) }, { id: 'multi-hashline' }),
      { stopReason: 'toolUse' },
    ),
    fauxAssistantMessage('MULTI_DONE'),
  ]);
  pi.registerProvider(faux.provider);
  pi.on('tool_call', (event) => { if (event.toolName === 'hashline') log(); });
}
