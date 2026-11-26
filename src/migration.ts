import { copyFileSync, readFileSync, renameSync, writeFileSync } from 'node:fs';

import type { ToolUiConfig } from './config.js';
import { isRecord } from './guards.js';

export interface MigrationResult {
  backup: string;
}

export function migrateSettingsFile(path: string, config: ToolUiConfig, stamp = Date.now()): MigrationResult {
  const original = readFileSync(path, 'utf8');
  const parsed: unknown = JSON.parse(original);
  if (!isRecord(parsed)) throw new Error('settings.json 顶层不是对象');
  const backup = `${path}.bak-${stamp}`;
  copyFileSync(path, backup);
  const temporary = `${path}.tmp-${stamp}`;
  writeFileSync(temporary, `${JSON.stringify({ ...parsed, toolUi: config }, null, 2)}\n`);
  renameSync(temporary, path);
  return { backup };
}
