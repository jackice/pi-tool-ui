import type { AgentToolResult, Theme, ToolRenderResultOptions } from '@earendil-works/pi-coding-agent';
import { BashView, fromPiTheme } from '@jackice/pi-ui';

import { adaptBash } from '../adapters/bash.js';
import type { RendererLike, RendererPatch } from '../integration/resolver.js';

interface ResultContext {
  state: Record<PropertyKey, unknown>;
  args: unknown;
  toolCallId: string;
  durationMs?: number;
  cwd?: string;
  isError?: boolean;
}

const cacheKey = Symbol('pi-tool-ui-bash');

interface Cached {
  content: unknown;
  details: unknown;
  expanded: boolean;
  theme: Theme;
  view: BashView;
}

export function createBashFactory(): (original: RendererLike) => RendererPatch {
  return (original) => ({
    renderResult(result: AgentToolResult<unknown>, options: ToolRenderResultOptions, theme: Theme, context: ResultContext) {
      try {
        const cached = context.state[cacheKey] as Cached | undefined;
        const same = cached !== undefined && cached.content === result.content && cached.details === result.details;
        if (same && cached.expanded === options.expanded && cached.theme === theme) return cached.view;
        const model = adaptBash({
          args: context.args,
          result: { content: result.content, details: result.details },
          options: { isPartial: options.isPartial, expanded: options.expanded },
          context: { isError: context.isError, durationMs: context.durationMs, cwd: context.cwd },
        });
        const view = new BashView(fromPiTheme(theme), { model, expanded: options.expanded });
        context.state[cacheKey] = { content: result.content, details: result.details, expanded: options.expanded, theme, view };
        return view;
      } catch {
        // 适配或渲染失败时交还原生 renderer。
      }
      if (original.renderResult !== undefined) return original.renderResult(result, options, theme, context);
      return undefined;
    },
  } as RendererPatch);
}

export const bashFactory = createBashFactory();
