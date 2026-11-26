import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, expect, test } from 'vitest';

import { DEFAULT_CONFIG } from '../../src/config.js';
import { migrateSettingsFile } from '../../src/migration.js';

function settingsFile(content: object): string {
  const dir = mkdtempSync(join(tmpdir(), 'pi-tool-ui-migrate-'));
  const path = join(dir, 'settings.json');
  writeFileSync(path, JSON.stringify(content, null, 2));
  return path;
}

describe('一次性迁移', () => {
  test('保留其他配置并写入 toolUi 与备份', () => {
    const path = settingsFile({ theme: 'dark', editDiff: { nativeEdit: true } });
    const original = readFileSync(path, 'utf8');
    const config = structuredClone(DEFAULT_CONFIG);
    config.enabled = true;
    config.tools.edit.enabled = true;
    const result = migrateSettingsFile(path, config, 1234);
    const written = JSON.parse(readFileSync(path, 'utf8'));
    expect(written.theme).toBe('dark');
    expect(written.editDiff).toEqual({ nativeEdit: true });
    expect(written.toolUi.tools.edit.enabled).toBe(true);
    expect(readFileSync(result.backup, 'utf8')).toBe(original);
  });

  test('无效 JSON 不覆盖原文件', () => {
    const path = settingsFile({});
    writeFileSync(path, '{oops');
    expect(() => migrateSettingsFile(path, structuredClone(DEFAULT_CONFIG))).toThrow();
    expect(readFileSync(path, 'utf8')).toBe('{oops');
  });
});
