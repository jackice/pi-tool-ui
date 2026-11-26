import { describe, expect, test } from 'vitest';

import { createDiffFactory } from '../../src/renderers/diff.js';

const theme = { fg: (_token: string, text: string) => text, bold: (text: string) => text };
const options = { isPartial: false, expanded: false };
const context = { state: {}, args: { path: 'notes.txt' }, toolCallId: 'call-1' };
const sentinel = { kind: 'peer-result' };

function throwingDetails(): unknown {
  return new Proxy({}, { get() { throw new Error('adapter failure'); } });
}

describe('Diff 渲染失败回退', () => {
  test('Edit 适配器抛错时调用原 renderResult', () => {
    const factory = createDiffFactory('edit')({ renderResult: () => sentinel });
    const result = factory.renderResult!(
      { content: [{ type: 'text', text: 'native' }], details: throwingDetails() },
      options,
      theme,
      context,
    );
    expect(result).toBe(sentinel);
  });

  test('Hashline 适配器抛错时调用原 renderResult', () => {
    const factory = createDiffFactory('hashline')({ renderResult: () => sentinel });
    const result = factory.renderResult!(
      { content: [{ type: 'text', text: 'native' }], details: throwingDetails() },
      options,
      theme,
      context,
    );
    expect(result).toBe(sentinel);
  });
});
