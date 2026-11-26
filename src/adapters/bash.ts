import type { BashTruncation, BashViewModel } from '@jackice/pi-ui';

interface ContentBlock {
  type: string;
  text?: string;
}

interface BashTruncationDetails {
  totalLines: number;
  outputLines: number;
  totalBytes?: number;
  outputBytes?: number;
}

export interface BashAdapterInput {
  args: unknown;
  result: { content: readonly ContentBlock[]; details?: unknown };
  options: { isPartial: boolean; expanded: boolean };
  context: { isError?: boolean; durationMs?: number; cwd?: string };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function finite(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function truncationOf(details: unknown): BashTruncation | undefined {
  if (!isRecord(details) || !isRecord(details.truncation)) return undefined;
  const source = details.truncation;
  const totalLines = finite(source.totalLines);
  const outputLines = finite(source.outputLines);
  if (totalLines === undefined || outputLines === undefined) return undefined;
  const totalBytes = finite(source.totalBytes);
  const outputBytes = finite(source.outputBytes);
  return {
    totalLines,
    outputLines,
    ...(totalBytes === undefined ? {} : { totalBytes }),
    ...(outputBytes === undefined ? {} : { outputBytes }),
  };
}

function fullOutputPathOf(details: unknown): string | undefined {
  return isRecord(details) && typeof details.fullOutputPath === 'string' ? details.fullOutputPath : undefined;
}

export function adaptBash(input: BashAdapterInput): BashViewModel {
  const command = isRecord(input.args) && typeof input.args.command === 'string' ? input.args.command : undefined;
  const output = input.result.content
    .filter((block) => block.type === 'text' && typeof block.text === 'string')
    .map((block) => block.text ?? '')
    .join('\n');
  const error = input.context.isError === true;
  const status = error ? 'error' : input.options.isPartial ? 'running' : 'success';
  const durationMs = finite(input.context.durationMs);
  const truncation = truncationOf(input.result.details);
  const fullOutputPath = fullOutputPathOf(input.result.details);
  const cwd = typeof input.context.cwd === 'string' ? input.context.cwd : undefined;
  return {
    status,
    ...(command === undefined ? {} : { command }),
    output,
    ...(durationMs === undefined ? {} : { durationMs }),
    ...(cwd === undefined ? {} : { cwd }),
    ...(truncation === undefined ? {} : { truncation }),
    ...(fullOutputPath === undefined ? {} : { fullOutputPath }),
  };
}
