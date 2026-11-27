import type { AgentToolResult, Theme, ToolRenderResultOptions } from '@earendil-works/pi-coding-agent';
import type * as ReadViewModule from '@jackice/pi-ui/views/read';
import type * as ThemeModule from '@jackice/pi-ui/core/theme';

import { adaptRead } from '../adapters/read.js';
import { DEFAULT_CONFIG, type ToolUiConfig } from '../config.js';
import { loadPiUi } from '../integration/pi-ui-lazy.js';
import type { RendererLike, RendererPatch } from '../integration/resolver.js';

interface ResultContext {
  state: Record<PropertyKey, unknown>;
  args: unknown;
  toolCallId: string;
  isError?: boolean;
}

const cacheKey = Symbol('pi-tool-ui-read');

interface Cached {
  content: unknown;
  details: unknown;
  expanded: boolean;
  isError: boolean;
  args: unknown;
  config: string;
  theme: Theme;
  view: import('@jackice/pi-ui/views/read').ReadView;
}

export interface ReadDeps {
  highlightCode: (code: string, language?: string) => readonly string[];
  getLanguageFromPath: (path: string) => string | undefined;
  Container: new () => { render(width: number): string[] };
}

export const defaultReadDeps: ReadDeps = {
  highlightCode: () => [],
  getLanguageFromPath: () => undefined,
  Container: class { render() { return []; } } as never,
};

const IMAGE_EXTENSION = /\.(?:png|jpe?g|gif|webp|bmp|tiff?)$/i;

export function createReadFactory(getConfig: () => ToolUiConfig = () => DEFAULT_CONFIG, deps: ReadDeps = defaultReadDeps): (original: RendererLike) => RendererPatch {
  return (original) => ({
    renderCall(args: unknown, theme: Theme, context: { state: Record<PropertyKey, unknown> }) {
      const record = typeof args === 'object' && args !== null ? args as Record<string, unknown> : {};
      const path = typeof record.path === 'string' ? record.path : '';
      if (IMAGE_EXTENSION.test(path)) return original.renderCall?.(args, theme, context);
      return new deps.Container();
    },
    renderResult(result: AgentToolResult<unknown>, options: ToolRenderResultOptions, theme: Theme, context: ResultContext) {
      if (result.content.some((block) => block.type === 'image')) {
        return original.renderResult?.(result, options, theme, context);
      }
      try {
        const read = getConfig().tools.read;
        const config = JSON.stringify(read);
        const cached = context.state[cacheKey] as Cached | undefined;
        const same = cached !== undefined
          && cached.content === result.content
          && cached.details === result.details
          && cached.expanded === options.expanded
          && cached.isError === context.isError
          && cached.args === context.args
          && cached.config === config
          && cached.theme === theme;
        if (same) return cached.view;
        const model = adaptRead({
          args: context.args,
          result: { content: result.content, details: result.details },
          options: { isPartial: options.isPartial, expanded: options.expanded },
          context: { isError: context.isError },
        });
        const { ReadView } = loadPiUi<typeof ReadViewModule>('@jackice/pi-ui/views/read');
        const { fromPiTheme } = loadPiUi<typeof ThemeModule>('@jackice/pi-ui/core/theme');
        if (model.language === undefined && model.path !== undefined) {
          const language = deps.getLanguageFromPath(model.path);
          if (language !== undefined) model.language = language;
        }
        const view = new ReadView(fromPiTheme(theme), {
          model,
          expanded: options.expanded,
          config: {
            previewLines: read.previewLines,
            maxPreviewRows: read.maxPreviewRows,
            lineNumbers: read.lineNumbers,
            showPath: true,
            ...(read.highlight ? { highlighter: (code: string, language?: string) => deps.highlightCode(code, language) } : {}),
          },
        });
        context.state[cacheKey] = {
          content: result.content, details: result.details, expanded: options.expanded,
          isError: context.isError === true, args: context.args, config, theme, view,
        };
        return view;
      } catch {
        // 失败回退原生 renderer。
      }
      return original.renderResult?.(result, options, theme, context);
    },
  } as RendererPatch);
}
