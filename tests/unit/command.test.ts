import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, expect, test } from 'vitest';

import extension from '../../src/index.js';

interface Command {
  handler: (args: string, ctx: unknown) => Promise<void>;
}

function setup(settings: object) {
  const dir = mkdtempSync(join(tmpdir(), 'pi-tool-ui-command-'));
  writeFileSync(join(dir, 'settings.json'), JSON.stringify(settings, null, 2));
  process.env.PI_CODING_AGENT_DIR = dir;
  const commands: Command[] = [];
  const notifications: string[] = [];
  const pi = {
    on: () => undefined,
    registerToolRenderer: () => undefined,
    getSettings: () => settings,
    registerCommand: (_name: string, definition: Command) => { commands.push(definition); },
  };
  return { dir, notifications, pi, commands };
}

const ctx = (notifications: string[], confirmed: boolean) => ({
  ui: {
    notify: (message: string) => { notifications.push(message); },
    confirm: async () => confirmed,
  },
});

describe('tool-ui-migrate 命令', () => {
  test('force 确认后备份并写入配置', async () => {
    const { dir, notifications, pi, commands } = setup({ editDiff: { nativeEdit: true } });
    await extension(pi as never);
    await commands[0]!.handler('force', ctx(notifications, true));
    const written = JSON.parse(readFileSync(join(dir, 'settings.json'), 'utf8'));
    expect(written.toolUi.tools.edit.enabled).toBe(true);
    expect(written.toolUi.tools.hashline.enabled).toBe(true);
    expect(notifications.some((item) => item.includes('已迁移'))).toBe(true);
  });

  test('dry 只预览不写入', async () => {
    const { dir, notifications, pi, commands } = setup({ editDiff: { nativeEdit: true } });
    await extension(pi as never);
    await commands[0]!.handler('dry', ctx(notifications, true));
    expect(JSON.parse(readFileSync(join(dir, 'settings.json'), 'utf8')).toolUi).toBeUndefined();
    expect(notifications.some((item) => item.startsWith('schema: v1'))).toBe(true);
  });

  test('取消不写入', async () => {
    const { dir, pi, commands } = setup({ editDiff: { nativeEdit: true } });
    await extension(pi as never);
    await commands[0]!.handler('force', ctx([], false));
    expect(JSON.parse(readFileSync(join(dir, 'settings.json'), 'utf8')).toolUi).toBeUndefined();
  });
});
