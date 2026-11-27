import type { AgentToolResult, Theme, ToolRenderResultOptions } from '@earendil-works/pi-coding-agent';
import { Text } from '@earendil-works/pi-tui';
import { fromPiTheme } from '@jackice/pi-ui/core/theme';
import { adaptHashlineDetails, type EditViewModel } from '@jackice/pi-ui/diff';
import { EditView } from '@jackice/pi-ui/views/edit';

import { adaptNativeEdit } from '../adapters/native-edit.js';
import type { RendererLike, RendererPatch } from '../integration/resolver.js';

const cacheKey = Symbol('pi-tool-ui-diff');

interface CachedDiff {
  details: unknown;
  durationMs: number | undefined;
  theme: Theme;
  expanded: boolean;
  model: EditViewModel;
  view: EditView;
}

interface ResultContext {
  state: Record<PropertyKey, unknown>;
  args: unknown;
  toolCallId: string;
  durationMs?: number;
  isError?: boolean;
}

export type DiffFactory = (original: RendererLike) => RendererPatch;

export function createDiffFactory(mode: 'edit' | 'hashline'): DiffFactory {
  const native = mode === 'edit';
  return (original) => ({
    ...(native ? {} : { renderShell: 'self' as const }),
    renderResult(result: AgentToolResult<unknown>, options: ToolRenderResultOptions, theme: Theme, context: ResultContext) {
      try {
      if (!options.isPartial && (!native || !context.isError)) {
        const cached = context.state[cacheKey] as CachedDiff | undefined;
        const { durationMs, toolCallId } = context;
        const sameResult = cached !== undefined && cached.details === result.details && cached.durationMs === durationMs;
        if (sameResult && cached.theme === theme && cached.expanded === options.expanded) return cached.view;
        const timing = { toolCallId, ...(durationMs === undefined ? {} : { durationMs }) };
        const model = sameResult ? cached.model : native
          ? adaptNativeEdit(result.details, context.args, timing)
          : adaptHashlineDetails(result.details, timing);
        if (model !== undefined) {
          const view = new EditView(fromPiTheme(theme), { model, expanded: options.expanded });
          context.state[cacheKey] = { details: result.details, durationMs, theme, expanded: options.expanded, model, view };
          return view;
        }
      }
      } catch {
        // 下游 renderer 是安全回退；异常不能冒泡到宿主。
      }
      if (original.renderResult !== undefined) return original.renderResult(result, options, theme, context);
      const text = result.content.flatMap((block) => block.type === 'text' ? [block.text] : []).join('\n');
      return new Text(theme.fg('toolOutput', text), 0, 0);
    },
  } as RendererPatch);
}

export const editFactory = createDiffFactory('edit');
export const hashlineFactory = createDiffFactory('hashline');
