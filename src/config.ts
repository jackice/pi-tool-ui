import { isRecord } from './guards.js';

export interface EditConfig {
  enabled: boolean;
}

export interface BashConfig {
  enabled: boolean;
  command: { highlight: boolean; previewRows: number };
  output: {
    previewRows: number;
    ansi: boolean;
    showTruncation: boolean;
    showFullOutputPath: boolean;
  };
  showDuration: boolean;
  showCwd: boolean;
}

export interface WriteConfig {
  enabled: boolean;
  highlight: boolean;
  lineNumbers: boolean;
  previewLines: number;
  streamingPreviewLines: number;
  maxPreviewRows: number;
}

export interface ReadConfig {
  enabled: boolean;
  highlight: boolean;
  lineNumbers: boolean;
  previewLines: number;
  maxPreviewRows: number;
  hideHashAnchors: boolean;
}

export interface ToolUiConfig {
  enabled: boolean;
  tools: {
    edit: EditConfig;
    hashline: EditConfig;
    bash: BashConfig;
    write: WriteConfig;
    read: ReadConfig;
  };
}

export type ToolName = keyof ToolUiConfig['tools'];

export interface LegacyInput {
  toolUi?: unknown;
  editDiff?: { nativeEdit?: unknown };
  envHashline?: string | undefined;
  legacy?: boolean;
}

export interface LegacyResult {
  config: ToolUiConfig;
  source: 'new' | 'legacy' | 'default';
  diagnostics: string[];
}

type Record_ = Record<string, unknown>;

export const DEFAULT_CONFIG: ToolUiConfig = Object.freeze({
  enabled: false,
  tools: Object.freeze({
    edit: Object.freeze({ enabled: false }),
    hashline: Object.freeze({ enabled: false }),
    bash: Object.freeze({
      enabled: false,
      command: Object.freeze({ highlight: true, previewRows: 6 }),
      output: Object.freeze({ previewRows: 12, ansi: true, showTruncation: true, showFullOutputPath: true }),
      showDuration: true,
      showCwd: false,
    }),
    write: Object.freeze({
      enabled: false,
      highlight: true,
      lineNumbers: true,
      previewLines: 6,
      streamingPreviewLines: 12,
      maxPreviewRows: 18,
    }),
    read: Object.freeze({
      enabled: false,
      highlight: true,
      lineNumbers: true,
      previewLines: 12,
      maxPreviewRows: 24,
      hideHashAnchors: false,
    }),
  }),
}) as ToolUiConfig;

export function cloneDefaultConfig(): ToolUiConfig {
  return structuredClone(DEFAULT_CONFIG);
}

function readBoolean(value: unknown, fallback: boolean): boolean | undefined {
  if (value === undefined) return fallback;
  return typeof value === 'boolean' ? value : undefined;
}

function readPreview(value: unknown, fallback: number): number | undefined {
  if (value === undefined) return fallback;
  return typeof value === 'number' && Number.isInteger(value) && value >= 1 && value <= 100 ? value : undefined;
}

function hasUnknownKeys(value: Record_, allowed: readonly string[]): boolean {
  return Object.keys(value).some((key) => !allowed.includes(key));
}

function parseCommon(value: unknown, allowed: readonly string[]): { enabled: boolean } | undefined {
  if (!isRecord(value) || hasUnknownKeys(value, ['enabled', ...allowed])) return undefined;
  const enabled = readBoolean(value.enabled, false);
  return enabled === undefined ? undefined : { enabled };
}

function parseEditTool(value: unknown): { enabled: boolean } | undefined {
  return parseCommon(value, []);
}

function parseBashTool(value: unknown): BashConfig | undefined {
  const common = parseCommon(value, ['command', 'output', 'showDuration', 'showCwd']);
  if (!common) return undefined;
  const record = value as Record_;
  const command = record.command ?? {};
  const output = record.output ?? {};
  if (!isRecord(command) || !isRecord(output)) return undefined;
  if (hasUnknownKeys(command, ['highlight', 'previewRows']) || hasUnknownKeys(output, ['previewRows', 'ansi', 'showTruncation', 'showFullOutputPath'])) return undefined;
  const values = {
    commandHighlight: readBoolean(command.highlight, true),
    commandRows: readPreview(command.previewRows, 6),
    outputRows: readPreview(output.previewRows, 12),
    ansi: readBoolean(output.ansi, true),
    showTruncation: readBoolean(output.showTruncation, true),
    showFullOutputPath: readBoolean(output.showFullOutputPath, true),
    showDuration: readBoolean(record.showDuration, true),
    showCwd: readBoolean(record.showCwd, false),
  };
  if (Object.values(values).some((item) => item === undefined)) return undefined;
  return {
    enabled: common.enabled,
    command: { highlight: values.commandHighlight as boolean, previewRows: values.commandRows as number },
    output: {
      previewRows: values.outputRows as number,
      ansi: values.ansi as boolean,
      showTruncation: values.showTruncation as boolean,
      showFullOutputPath: values.showFullOutputPath as boolean,
    },
    showDuration: values.showDuration as boolean,
    showCwd: values.showCwd as boolean,
  };
}

function parseWriteTool(value: unknown): WriteConfig | undefined {
  const common = parseCommon(value, ['highlight', 'lineNumbers', 'previewLines', 'streamingPreviewLines', 'maxPreviewRows']);
  if (!common) return undefined;
  const record = value as Record_;
  const values = {
    highlight: readBoolean(record.highlight, true),
    lineNumbers: readBoolean(record.lineNumbers, true),
    previewLines: readPreview(record.previewLines, 6),
    streamingPreviewLines: readPreview(record.streamingPreviewLines, 12),
    maxPreviewRows: readPreview(record.maxPreviewRows, 18),
  };
  if (Object.values(values).some((item) => item === undefined)) return undefined;
  return {
    enabled: common.enabled,
    highlight: values.highlight as boolean,
    lineNumbers: values.lineNumbers as boolean,
    previewLines: values.previewLines as number,
    streamingPreviewLines: values.streamingPreviewLines as number,
    maxPreviewRows: values.maxPreviewRows as number,
  };
}

function parseReadTool(value: unknown): ReadConfig | undefined {
  const common = parseCommon(value, ['highlight', 'lineNumbers', 'previewLines', 'maxPreviewRows', 'hideHashAnchors']);
  if (!common) return undefined;
  const record = value as Record_;
  const values = {
    highlight: readBoolean(record.highlight, true),
    lineNumbers: readBoolean(record.lineNumbers, true),
    previewLines: readPreview(record.previewLines, 12),
    maxPreviewRows: readPreview(record.maxPreviewRows, 24),
    hideHashAnchors: readBoolean(record.hideHashAnchors, false),
  };
  if (Object.values(values).some((item) => item === undefined)) return undefined;
  return {
    enabled: common.enabled,
    highlight: values.highlight as boolean,
    lineNumbers: values.lineNumbers as boolean,
    previewLines: values.previewLines as number,
    maxPreviewRows: values.maxPreviewRows as number,
    hideHashAnchors: values.hideHashAnchors as boolean,
  };
}

const parsers = {
  edit: parseEditTool,
  hashline: parseEditTool,
  bash: parseBashTool,
  write: parseWriteTool,
  read: parseReadTool,
} as const;

export function parseToolUiConfig(raw: unknown, diagnostics: string[]): ToolUiConfig {
  const config = structuredClone(DEFAULT_CONFIG);
  if (!isRecord(raw)) {
    diagnostics.push('toolUi 必须是对象，已关闭全部工具');
    return config;
  }
  if (hasUnknownKeys(raw, ['enabled', 'tools'])) {
    diagnostics.push('toolUi 含未知键，已关闭全部工具');
    return config;
  }
  const enabled = readBoolean(raw.enabled, false);
  if (enabled === undefined) {
    diagnostics.push('toolUi.enabled 必须是布尔值，已关闭全部工具');
    return config;
  }
  const tools = raw.tools ?? {};
  if (!isRecord(tools)) {
    diagnostics.push('toolUi.tools 必须是对象，已关闭全部工具');
    return config;
  }
  for (const name of Object.keys(tools)) {
    if (!(name in parsers)) diagnostics.push(`toolUi.tools.${name} 未知，已忽略`);
  }
  for (const [name, parse] of Object.entries(parsers) as [ToolName, (value: unknown) => { enabled: boolean } | undefined][]) {
    const value = tools[name];
    if (value === undefined) continue;
    const parsed = parse(value);
    if (!parsed) {
      diagnostics.push(`toolUi.tools.${name} 配置无效，已关闭该工具`);
      continue;
    }
    config.tools[name] = parsed as never;
  }
  config.enabled = enabled;
  return config;
}

function legacyValues(input: LegacyInput): { edit: boolean; hashline: boolean } {
  return {
    edit: input.editDiff?.nativeEdit === true,
    hashline: input.envHashline !== '0',
  };
}

export function mapLegacyConfig(input: LegacyInput): LegacyResult {
  if (input.toolUi !== undefined) {
    const diagnostics: string[] = [];
    const config = parseToolUiConfig(input.toolUi, diagnostics);
    if (input.editDiff !== undefined || input.envHashline !== undefined) {
      const legacy = legacyValues(input);
      if (config.tools.edit.enabled !== legacy.edit) diagnostics.push('toolUi.tools.edit 与 editDiff.nativeEdit 冲突，采用 toolUi');
      if (config.tools.hashline.enabled !== legacy.hashline) diagnostics.push('toolUi.tools.hashline 与环境开关冲突，采用 toolUi');
    }
    return { config, source: 'new', diagnostics };
  }
  if (!input.legacy && input.editDiff === undefined && input.envHashline === undefined) {
    return { config: structuredClone(DEFAULT_CONFIG), source: 'default', diagnostics: [] };
  }
  const legacy = legacyValues(input);
  const config = structuredClone(DEFAULT_CONFIG);
  config.tools.edit.enabled = legacy.edit;
  config.tools.hashline.enabled = legacy.hashline;
  config.enabled = legacy.edit || legacy.hashline;
  return { config, source: 'legacy', diagnostics: [] };
}
