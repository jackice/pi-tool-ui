import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';

import { cloneDefaultConfig, mapLegacyConfig, type ToolUiConfig } from './config.js';
import { createResolver, type RendererLike } from './integration/resolver.js';
import { editFactory, hashlineFactory } from './renderers/diff.js';

interface Settings {
  toolUi?: unknown;
  editDiff?: { nativeEdit?: unknown };
}

export default async function (pi: ExtensionAPI) {
  let config: ToolUiConfig = cloneDefaultConfig();
  pi.on('session_start', () => {
    const settings = pi.getSettings() as Settings;
    config = mapLegacyConfig({
      toolUi: settings.toolUi,
      editDiff: settings.editDiff,
      envHashline: process.env.PI_HASHLINE_DIFF,
    }).config;
  });
  pi.registerToolRenderer(createResolver(() => config, {
    edit: editFactory,
    hashline: hashlineFactory,
  }) as never);
}
