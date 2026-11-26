import type { WriteViewModel } from '@jackice/pi-ui';
import { getLanguageFromPath } from '@earendil-works/pi-coding-agent';

interface ContentBlock {
  type: string;
  text?: string;
}

export interface WriteAdapterInput {
  args: unknown;
  result: { content: readonly ContentBlock[]; details?: unknown };
  options: { isPartial: boolean; expanded: boolean; argsComplete: boolean };
  context: { isError?: boolean };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function normalizeContent(content: string): string {
  return content.replace(/\r\n/g, '\n');
}

function countLines(content: string): number {
  if (content.length === 0) return 0;
  const lines = content.split('\n');
  return content.endsWith('\n') ? lines.length - 1 : lines.length;
}

export function adaptWrite(input: WriteAdapterInput): WriteViewModel {
  const args = isRecord(input.args) ? input.args : {};
  const path = typeof args.path === 'string' ? args.path : undefined;
  const rawContent = typeof args.content === 'string' ? args.content : undefined;
  const content = rawContent === undefined ? undefined : normalizeContent(rawContent);
  const error = input.context.isError === true;
  const status = error
    ? 'error'
    : input.options.isPartial
      ? input.options.argsComplete === false ? 'streaming' : 'running'
      : 'success';
  const notices = error
    ? input.result.content
      .filter((block) => block.type === 'text' && typeof block.text === 'string')
      .map((block) => block.text ?? '')
      .filter((text) => text.length > 0)
    : [];
  const language = path === undefined ? undefined : getLanguageFromPath(path);
  return {
    status,
    ...(path === undefined ? {} : { path }),
    ...(content === undefined ? {} : { content }),
    argsComplete: input.options.argsComplete,
    ...(content === undefined ? {} : { lineCount: countLines(content) }),
    ...(language === undefined ? {} : { language }),
    ...(notices.length === 0 ? {} : { notices }),
  };
}
