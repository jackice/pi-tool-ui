import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai';

export default function (pi: ExtensionAPI) {
  const faux = fauxProvider({ provider: 'tool-ui-probe', models: [{ id: 'local' }] });
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('subagent', { action: 'list' }, { id: 'mixed-subagent' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage(fauxToolCall('get_goal', {}, { id: 'mixed-goal' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage(fauxToolCall('session_todo', {
      action: 'init',
      phases: [{ name: 'Phase', tasks: [{ content: 'MIXED_TODO_TASK' }] }],
    }, { id: 'mixed-todo' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage(fauxToolCall('write', { path: 'mixed.txt', content: 'mixed-alpha\nmixed-beta\n' }, { id: 'mixed-write' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage(fauxToolCall('read', { path: 'mixed.txt' }, { id: 'mixed-read' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('MIXED_DONE'),
  ]);
  pi.registerProvider(faux.provider);
}
