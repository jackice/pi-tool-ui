import type { ToolName, ToolUiConfig } from '../config.js';

export interface RendererLike {
  renderShell?: 'default' | 'self';
  renderCall?: (...args: unknown[]) => unknown;
  renderResult?: (...args: unknown[]) => unknown;
  [key: string]: unknown;
}

export type RendererPatch = Partial<RendererLike>;
export type RendererFactory = (original: RendererLike) => RendererPatch;
export type ToolRendererResolver = <T extends RendererLike | undefined>(name: string, next: () => T) => T;

const allowed: Partial<Record<ToolName, readonly (keyof RendererLike)[]>> = {
  edit: ['renderResult'],
  hashline: ['renderShell', 'renderResult'],
  bash: ['renderResult'],
  write: ['renderCall', 'renderResult'],
};

export function createResolver(getConfig: () => ToolUiConfig, factories: Partial<Record<ToolName, RendererFactory>>): ToolRendererResolver {
  return (name, next) => {
    const original = next();
    if (original === undefined) return original;
    const config = getConfig();
    if (!config.enabled || !(name in factories)) return original;
    const tool = name as ToolName;
    if (!config.tools[tool].enabled) return original;
    const patch = factories[tool]!(original);
    const merged = { ...original } as RendererLike;
    for (const field of allowed[tool] ?? []) {
      if (field in patch) merged[field] = patch[field];
    }
    return merged as typeof original;
  };
}
