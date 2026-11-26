import { describe, expect, test } from 'vitest';

import { DEFAULT_CONFIG, type ToolUiConfig } from '../../src/config.js';
import { createResolver, type RendererLike } from '../../src/integration/resolver.js';

const original: RendererLike = {
  renderShell: 'default',
  renderCall: () => 'call',
  renderResult: () => 'result',
};

function config(patch: Partial<ToolUiConfig['tools']> = {}): ToolUiConfig {
  const value = structuredClone(DEFAULT_CONFIG);
  value.enabled = true;
  Object.assign(value.tools, patch);
  return value;
}

const factory = () => ({ renderResult: () => 'custom', renderCall: () => 'hijacked', renderShell: 'self' as const });

describe('renderer resolver', () => {
  test('全局或多工具关闭时返回原对象', () => {
    const off = createResolver(() => structuredClone(DEFAULT_CONFIG), { edit: factory });
    expect(off('edit', () => original)).toBe(original);
    const disabledTool = createResolver(() => config(), { edit: factory });
    expect(disabledTool('edit', () => original)).toBe(original);
  });

  test('未知工具与无下游时保持原样', () => {
    const resolve = createResolver(() => config({ edit: { enabled: true } }), { edit: factory });
    expect(resolve('bash', () => original)).toBe(original);
    expect(resolve('edit', () => undefined)).toBeUndefined();
  });

  test('Edit 只替换 renderResult，保留 shell 与 call', () => {
    const resolve = createResolver(() => config({ edit: { enabled: true } }), { edit: factory });
    const result = resolve('edit', () => original)!;
    expect(result.renderResult).not.toBe(original.renderResult);
    expect(result.renderCall).toBe(original.renderCall);
    expect(result.renderShell).toBe('default');
  });

  test('Hashline 允许替换 shell 与 renderResult', () => {
    const resolve = createResolver(() => config({ hashline: { enabled: true } }), { hashline: factory });
    const result = resolve('hashline', () => original)!;
    expect(result.renderShell).toBe('self');
    expect(result.renderResult).not.toBe(original.renderResult);
    expect(result.renderCall).toBe(original.renderCall);
  });

  test('每次 next 恰好调用一次', () => {
    let calls = 0;
    const resolve = createResolver(() => config({ edit: { enabled: true } }), { edit: factory });
    resolve('edit', () => {
      calls += 1;
      return original;
    });
    expect(calls).toBe(1);
  });
});
