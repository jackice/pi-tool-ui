import type { AgentToolResult, Theme, ToolRenderResultOptions } from '@earendil-works/pi-coding-agent';
import type * as DiffModule from '@jackice/pi-ui/diff';
import type * as ThemeModule from '@jackice/pi-ui/core/theme';
import type * as EditViewModule from '@jackice/pi-ui/views/edit';

import { adaptNativeEdit } from '../adapters/native-edit.js';
import { loadPiUi } from '../integration/pi-ui-lazy.js';
import type { RendererLike, RendererPatch } from '../integration/resolver.js';

const cacheKey = Symbol('pi-tool-ui-diff');

interface CachedDiff {
  details: unknown;
  durationMs: number | undefined;
  theme: Theme;
  expanded: boolean;
  model: DiffModule.EditViewModel;
  view: EditViewModule.EditView;
}

interface ResultContext {
  state: Record<PropertyKey, unknown>;
  args: unknown;
  toolCallId: string;
  durationMs?: number;
  isError?: boolean;
}

export type DiffFactory = (original: RendererLike) => RendererPatch;

export interface DiffDeps { Text: new (text: string, paddingX: number, paddingY: number) => { render(width: number): string[] } }

export function createDiffFactory(mode: 'edit' | 'hashline', deps: DiffDeps = { Text: class { constructor(public text: string) {} render() { return [this.text]; } } as never }): DiffFactory {
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
          : loadPiUi<typeof DiffModule>('@jackice/pi-ui/diff').adaptHashlineDetails(result.details, timing);
        if (model !== undefined) {
          const { EditView } = loadPiUi<typeof EditViewModule>('@jackice/pi-ui/views/edit');
          const { fromPiTheme } = loadPiUi<typeof ThemeModule>('@jackice/pi-ui/core/theme');
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
      return new deps.Text(theme.fg('toolOutput', text), 0, 0);
    },
  } as RendererPatch);
}

export const editFactory = createDiffFactory('edit');
export const hashlineFactory = createDiffFactory('hashline');
