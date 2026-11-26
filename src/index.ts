import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';

import { cloneDefaultConfig, mapLegacyConfig, type ToolUiConfig } from './config.js';
import { createResolver } from './integration/resolver.js';
import { migrateSettingsFile, migrationReport } from './migration.js';
import { bashFactory } from './renderers/bash.js';
import { editFactory, hashlineFactory } from './renderers/diff.js';

interface Settings {
  toolUi?: unknown;
  editDiff?: { nativeEdit?: unknown };
}

function agentDir(): string {
  return process.env.PI_CODING_AGENT_DIR ?? join(homedir(), '.pi/agent');
}

export default async function (pi: ExtensionAPI) {
  let config: ToolUiConfig = cloneDefaultConfig();
  let announced = false;

  pi.on('session_start', (_, ctx) => {
    const settings = pi.getSettings() as Settings;
    if (existsSync(join(agentDir(), 'extensions/hashline-diff'))) {
      config = cloneDefaultConfig();
      if (!announced) {
        announced = true;
        ctx.ui.notify('toolUi: 检测到旧 hashline-diff，已禁用 tool-ui；移除旧扩展并重启后再启用', 'warning');
      }
      return;
    }
    const result = mapLegacyConfig({
      toolUi: settings.toolUi,
      editDiff: settings.editDiff,
      envHashline: process.env.PI_HASHLINE_DIFF,
    });
    config = result.config;
    if (!announced && result.diagnostics.length > 0) {
      announced = true;
      for (const item of result.diagnostics) ctx.ui.notify(`toolUi: ${item}`, 'warning');
    }
  });

  pi.registerCommand('tool-ui-migrate', {
    description: 'Dry-run or apply one-time migration from hashline-diff settings',
    handler: async (args, ctx) => {
      const settings = pi.getSettings() as Settings;
      const action = args.trim().toLowerCase();
      if (settings.toolUi !== undefined && action !== 'force') {
        ctx.ui.notify('toolUi 已配置；如需覆盖请执行 /tool-ui-migrate force', 'warning');
        return;
      }
      const result = mapLegacyConfig({
        toolUi: undefined,
        editDiff: settings.editDiff,
        envHashline: process.env.PI_HASHLINE_DIFF,
        legacy: true,
      });
      const report = migrationReport({
        nativeEdit: settings.editDiff?.nativeEdit,
        envHashline: process.env.PI_HASHLINE_DIFF,
        config: result.config,
      });
      if (action === '' || action === 'dry') {
        for (const line of report) ctx.ui.notify(line, 'info');
        if (action === '') ctx.ui.notify('写入请执行 /tool-ui-migrate force', 'info');
        return;
      }
      if (action !== 'force') {
        ctx.ui.notify('用法: /tool-ui-migrate | /tool-ui-migrate dry | /tool-ui-migrate force', 'warning');
        return;
      }
      const confirmed = await ctx.ui.confirm('应用 toolUi 迁移？', `${report.join('\n')}\n\n将备份并写入 settings.json`);
      if (!confirmed) return;
      try {
        const { backup } = migrateSettingsFile(join(agentDir(), 'settings.json'), result.config);
        ctx.ui.notify(`toolUi 已迁移；备份 ${backup}`, 'info');
      } catch (error) {
        ctx.ui.notify(`迁移失败: ${error instanceof Error ? error.message : String(error)}`, 'error');
      }
    },
  });

  pi.registerToolRenderer(createResolver(() => config, {
    edit: editFactory,
    hashline: hashlineFactory,
    bash: bashFactory,
  }) as never);
}
