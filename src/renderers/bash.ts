import type { AgentToolResult, Theme, ToolRenderResultOptions } from '@earendil-works/pi-coding-agent';
import type * as BashViewModule from '@jackice/pi-ui/views/bash';
import type * as ThemeModule from '@jackice/pi-ui/core/theme';

import { adaptBash } from '../adapters/bash.js';
import { DEFAULT_CONFIG, type ToolUiConfig } from '../config.js';
import { loadPiUi } from '../integration/pi-ui-lazy.js';
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
  isPartial: boolean;
  isError: boolean;
  durationMs: number | undefined;
  args: unknown;
  config: string;
  theme: Theme;
  view: import('@jackice/pi-ui/views/bash').BashView;
}

export function createBashFactory(getConfig: () => ToolUiConfig = () => DEFAULT_CONFIG): (original: RendererLike) => RendererPatch {
  return (original) => ({
    renderResult(result: AgentToolResult<unknown>, options: ToolRenderResultOptions, theme: Theme, context: ResultContext) {
      try {
        const bash = getConfig().tools.bash;
        const config = JSON.stringify(bash);
        const cached = context.state[cacheKey] as Cached | undefined;
        const same = cached !== undefined
          && cached.content === result.content
          && cached.details === result.details
          && cached.expanded === options.expanded
          && cached.isPartial === options.isPartial
          && cached.isError === context.isError
          && cached.durationMs === context.durationMs
          && cached.args === context.args
          && cached.config === config
          && cached.theme === theme;
        if (same) return cached.view;
        const model = adaptBash({
          args: context.args,
          result: { content: result.content, details: result.details },
          options: { isPartial: options.isPartial, expanded: options.expanded },
          context: { isError: context.isError, durationMs: context.durationMs, cwd: context.cwd },
        });
        const { BashView } = loadPiUi<typeof BashViewModule>('@jackice/pi-ui/views/bash');
        const { fromPiTheme } = loadPiUi<typeof ThemeModule>('@jackice/pi-ui/core/theme');
        const view = new BashView(fromPiTheme(theme), {
          model,
          expanded: options.expanded,
          showCommand: false,
          config: {
            commandRows: bash.command.previewRows,
            outputRows: bash.output.previewRows,
            ansi: bash.output.ansi,
            showTruncation: bash.output.showTruncation,
            showFullOutputPath: bash.output.showFullOutputPath,
            showDuration: bash.showDuration,
            showCwd: bash.showCwd,
          },
        });
        context.state[cacheKey] = {
          content: result.content, details: result.details, expanded: options.expanded,
          isPartial: options.isPartial, isError: context.isError === true, durationMs: context.durationMs,
          args: context.args, config, theme, view,
        };
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
