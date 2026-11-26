import type { AgentToolResult, Theme, ToolRenderResultOptions } from '@earendil-works/pi-coding-agent';
import { Container } from '@earendil-works/pi-tui';
import { WriteView, fromPiTheme } from '@jackice/pi-ui';

import { adaptWrite } from '../adapters/write.js';
import { DEFAULT_CONFIG, type ToolUiConfig } from '../config.js';
import type { RendererLike, RendererPatch } from '../integration/resolver.js';

interface ResultContext {
  state: Record<PropertyKey, unknown>;
  args: unknown;
  toolCallId: string;
  argsComplete: boolean;
  isError?: boolean;
}

const cacheKey = Symbol('pi-tool-ui-write');
const callKey = Symbol('pi-tool-ui-write-call');

interface CachedCall {
  path: string;
  content: string | undefined;
  config: string;
  theme: Theme;
  view: WriteView;
}



interface Cached {
  content: unknown;
  details: unknown;
  expanded: boolean;
  isPartial: boolean;
  isError: boolean;
  argsComplete: boolean;
  args: unknown;
  config: string;
  theme: Theme;
  view: WriteView;
}

export function createWriteFactory(getConfig: () => ToolUiConfig = () => DEFAULT_CONFIG): (original: RendererLike) => RendererPatch {
  return (original) => ({
    renderCall(args: unknown, theme: Theme, context: { state: Record<PropertyKey, unknown>; argsComplete: boolean }) {
      if (context.argsComplete) return new Container();
      const record = typeof args === 'object' && args !== null ? args as Record<string, unknown> : {};
      const path = typeof record.path === 'string' ? record.path : undefined;
      const rawContent = typeof record.content === 'string' ? record.content : undefined;
      const content = rawContent === undefined ? undefined : rawContent.replace(/\r\n/g, '\n');
      const write = getConfig().tools.write;
      const config = JSON.stringify(write);
      const cached = context.state[callKey] as CachedCall | undefined;
      if (cached !== undefined && cached.path === (path ?? '') && cached.content === content && cached.config === config && cached.theme === theme) return cached.view;
      const lineCount = content === undefined || content.length === 0
        ? undefined
        : content.endsWith('\n') ? content.split('\n').length - 1 : content.split('\n').length;
      const view = new WriteView(fromPiTheme(theme), {
        model: {
          status: 'streaming',
          argsComplete: false,
          ...(path === undefined ? {} : { path }),
          ...(content === undefined ? {} : { content }),
          ...(lineCount === undefined ? {} : { lineCount }),
        },
        expanded: false,
        config: {
          previewLines: write.previewLines,
          streamingPreviewLines: write.streamingPreviewLines,
          maxPreviewRows: write.maxPreviewRows,
          lineNumbers: write.lineNumbers,
        },
      });
      context.state[callKey] = { path: path ?? '', content, config, theme, view };
      return view;
    },
    renderResult(result: AgentToolResult<unknown>, options: ToolRenderResultOptions, theme: Theme, context: ResultContext) {
      try {
        const write = getConfig().tools.write;
        const config = JSON.stringify(write);
        const cached = context.state[cacheKey] as Cached | undefined;
        const same = cached !== undefined
          && cached.content === result.content
          && cached.details === result.details
          && cached.expanded === options.expanded
          && cached.isPartial === options.isPartial
          && cached.isError === context.isError
          && cached.argsComplete === context.argsComplete
          && cached.args === context.args
          && cached.config === config
          && cached.theme === theme;
        if (same) return cached.view;
        const model = adaptWrite({
          args: context.args,
          result: { content: result.content, details: result.details },
          options: { isPartial: options.isPartial, expanded: options.expanded, argsComplete: context.argsComplete },
          context: { isError: context.isError },
        });
        const view = new WriteView(fromPiTheme(theme), {
          model,
          expanded: options.expanded,
          config: {
            previewLines: write.previewLines,
            streamingPreviewLines: write.streamingPreviewLines,
            maxPreviewRows: write.maxPreviewRows,
            lineNumbers: write.lineNumbers,
            showPath: true,
          },
        });
        context.state[cacheKey] = {
          content: result.content, details: result.details, expanded: options.expanded,
          isPartial: options.isPartial, isError: context.isError === true, argsComplete: context.argsComplete,
          args: context.args, config, theme, view,
        };
        return view;
      } catch {
        // 失败时回退原生 renderer。
      }
      if (original.renderResult !== undefined) return original.renderResult(result, options, theme, context);
      return undefined;
    },
  } as RendererPatch);
}
