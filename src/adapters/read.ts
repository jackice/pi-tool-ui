import type { ReadContentKind, ReadLine, ReadTruncation, ReadViewModel } from '@jackice/pi-ui';

interface ContentBlock {
  type: string;
  text?: string;
}

export interface ReadAdapterInput {
  args: unknown;
  result: { content: readonly ContentBlock[]; details?: unknown };
  options: { isPartial: boolean; expanded: boolean };
  context: { isError?: boolean };
}

const CONTINUATION_NOTICE = /^\[(?:Showing lines \d+-\d+ of \d+|-?\d+(?:\.\d+)? more lines in file)\. Use offset=-?\d+(?:\.\d+)? to continue\.\]$/;

const CODE_EXTENSIONS = new Set(['ts', 'tsx', 'js', 'jsx', 'json', 'rs', 'py', 'go', 'java', 'c', 'h', 'cpp', 'sh', 'css', 'html', 'yml', 'yaml', 'toml']);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function positiveInteger(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isInteger(value) && value >= 1 ? value : undefined;
}

function contentKind(path: string | undefined): ReadContentKind {
  if (path === undefined) return 'text';
  const extension = path.slice(path.lastIndexOf('.') + 1).toLowerCase();
  if (extension === 'md' || extension === 'markdown') return 'markdown-source';
  return CODE_EXTENSIONS.has(extension) ? 'code' : 'text';
}

function truncationOf(details: unknown): ReadTruncation | undefined {
  if (!isRecord(details) || !isRecord(details.truncation)) return undefined;
  const source = details.truncation;
  const outputLines = positiveInteger(source.outputLines) ?? (source.outputLines === 0 ? 0 : undefined);
  const totalLines = positiveInteger(source.totalLines) ?? (source.totalLines === 0 ? 0 : undefined);
  const maxLines = positiveInteger(source.maxLines);
  const maxBytes = positiveInteger(source.maxBytes);
  const by = source.truncatedBy === 'lines' || source.truncatedBy === 'bytes' ? source.truncatedBy : undefined;
  if (outputLines === undefined && totalLines === undefined && source.firstLineExceedsLimit !== true) return undefined;
  return {
    ...(outputLines === undefined ? {} : { outputLines }),
    ...(totalLines === undefined ? {} : { totalLines }),
    ...(source.firstLineExceedsLimit === true ? { firstLineExceedsLimit: true } : {}),
    ...(by === undefined ? {} : { by }),
    ...(maxLines === undefined ? {} : { maxLines }),
    ...(maxBytes === undefined ? {} : { maxBytes }),
  };
}

export function adaptRead(input: ReadAdapterInput): ReadViewModel {
  const args = isRecord(input.args) ? input.args : {};
  const path = typeof args.path === 'string' ? args.path : undefined;
  const text = input.result.content
    .filter((block) => block.type === 'text' && typeof block.text === 'string')
    .map((block) => block.text ?? '')
    .join('\n');
  const hasImage = input.result.content.some((block) => block.type === 'image');
  const truncation = truncationOf(input.result.details);
  const error = input.context.isError === true;

  if (error) {
    return { status: 'error', ...(path === undefined ? {} : { path }), source: 'native', contentKind: 'unknown', lines: [], ...(text === '' ? {} : { rawFallback: text }) };
  }
  if (hasImage) {
    return {
      status: 'success',
      ...(path === undefined ? {} : { path }),
      source: 'native',
      contentKind: input.result.content.length > 1 ? 'mixed' : 'image',
      lines: [],
      ...(text === '' ? {} : { rawFallback: text }),
    };
  }
  if (text.startsWith('Read image file [')) {
    return { status: 'success', ...(path === undefined ? {} : { path }), source: 'native', contentKind: 'unknown', lines: [], rawFallback: text };
  }
  if (/^\[[^\]]+#[0-9a-fA-F]+\]\n/.test(text)) {
    return { status: 'success', ...(path === undefined ? {} : { path }), source: 'hashline', contentKind: contentKind(path), lines: [], rawFallback: text };
  }
  if (truncation?.firstLineExceedsLimit === true) {
    return {
      status: 'success', ...(path === undefined ? {} : { path }), source: 'native', contentKind: contentKind(path), lines: [],
      truncation, ...(text === '' ? {} : { rawFallback: text }),
    };
  }

  const normalized = text.replace(/\r\n/g, '\n');
  const rawLines = normalized === '' ? [] : normalized.split('\n');
  if (rawLines.length > 1 && rawLines.at(-1) === '') rawLines.pop();
  let metaStart = rawLines.length;
  if (CONTINUATION_NOTICE.test(rawLines.at(-1) ?? '')) {
    metaStart = rawLines.length - 1;
    while (metaStart > 0 && rawLines[metaStart - 1] === '') metaStart--;
  }
  if (metaStart === 0) {
    return { status: 'success', ...(path === undefined ? {} : { path }), source: 'native', contentKind: contentKind(path), lines: [], ...(text === '' ? {} : { rawFallback: text }) };
  }
  const requestedOffset = positiveInteger(args.offset);
  const requestedLimit = positiveInteger(args.limit);
  const numbered = (args.limit === undefined || requestedLimit !== undefined)
    && (args.offset === undefined || args.offset === 0 || requestedOffset !== undefined);
  const start = requestedOffset ?? 1;
  const contentCount = truncation?.outputLines === undefined ? metaStart : Math.min(metaStart, truncation.outputLines);
  const lines: ReadLine[] = rawLines.map((line, index) => ({
    text: line,
    number: numbered && index < contentCount ? start + index : null,
  }));
  return {
    status: 'success',
    ...(path === undefined ? {} : { path }),
    ...(requestedOffset === undefined ? {} : { requestedOffset }),
    ...(requestedLimit === undefined ? {} : { requestedLimit }),
    source: 'native',
    contentKind: contentKind(path),
    lines,
    ...(truncation === undefined ? {} : { truncation }),
  };
}
