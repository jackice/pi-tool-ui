import { describe, expect, test } from 'vitest';

import { createBashFactory } from '../../src/renderers/bash.js';

const theme = { fg: (_token: string, text: string) => text, bold: (text: string) => text };
const options = { isPartial: false, expanded: false };
const sentinel = { kind: 'native-result' };

function context(overrides: Record<string, unknown> = {}) {
  return { state: {}, args: { command: 'pnpm test' }, toolCallId: 'call-1', isError: false, cwd: '/tmp', ...overrides };
}

const result = {
  content: [{ type: 'text', text: 'ok' }],
  details: { truncation: { totalLines: 10, outputLines: 10 } },
};

describe('Bash renderer', () => {
  test('相同内容复用同一 BashView', () => {
    const factory = createBashFactory();
    const patch = factory({ renderResult: () => sentinel });
    const ctx = context();
    const first = patch.renderResult!(result, options, theme, ctx);
    const second = patch.renderResult!(result, options, theme, ctx);
    expect(second).toBe(first);
  });

  test('内容或展开态变化生成新视图', () => {
    const factory = createBashFactory();
    const patch = factory({ renderResult: () => sentinel });
    const ctx = context();
    const first = patch.renderResult!(result, options, theme, ctx);
    const changed = patch.renderResult!(
      { content: [{ type: 'text', text: 'other' }], details: result.details },
      options,
      theme,
      ctx,
    );
    const expanded = patch.renderResult!(result, { isPartial: false, expanded: true }, theme, ctx);
    expect(changed).not.toBe(first);
    expect(expanded).not.toBe(first);
  });

  test('适配抛错时回退原 renderResult', () => {
    const factory = createBashFactory();
    const patch = factory({ renderResult: () => sentinel });
    const throwing = new Proxy({}, { get() { throw new Error('details failure'); } });
    const value = patch.renderResult!(
      { content: [], get details() { return throwing; } },
      options,
      theme,
      context(),
    );
    expect(value).toBe(sentinel);
  });
});
