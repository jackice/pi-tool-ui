import type { AgentToolResult, Theme, ToolRenderResultOptions } from '@earendil-works/pi-coding-agent';
import { highlightCode } from '@earendil-works/pi-coding-agent';
import { fromPiTheme } from '@jackice/pi-ui/core/theme';
import { ReadView } from '@jackice/pi-ui/views/read';

import { adaptRead } from '../adapters/read.js';
import { DEFAULT_CONFIG, type ToolUiConfig } from '../config.js';
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
  view: ReadView;
}

export function createReadFactory(getConfig: () => ToolUiConfig = () => DEFAULT_CONFIG): (original: RendererLike) => RendererPatch {
  return (original) => ({
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
        const view = new ReadView(fromPiTheme(theme), {
          model,
          expanded: options.expanded,
          config: {
            previewLines: read.previewLines,
            maxPreviewRows: read.maxPreviewRows,
            lineNumbers: read.lineNumbers,
            showPath: false,
            ...(read.highlight ? { highlighter: (code: string, language?: string) => highlightCode(code, language) } : {}),
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
