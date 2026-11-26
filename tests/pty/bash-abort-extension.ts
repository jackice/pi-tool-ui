import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';

export default function (pi: ExtensionAPI) {
  const delay = Number(process.env.PI_ABORT_AFTER_MS ?? '0');
  if (delay <= 0) throw new Error('PI_ABORT_AFTER_MS is required');
  pi.on('tool_call', (event, ctx) => {
    if (event.toolName !== 'bash') return;
    setTimeout(() => ctx.abort(), delay);
  });
}
