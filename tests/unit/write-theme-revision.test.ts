import type { Theme } from '@earendil-works/pi-coding-agent';
import { describe, expect, test } from 'vitest';

import { writeThemeRevision } from '../../src/renderers/write.js';

function theme(colors: Record<string, unknown>): Theme {
  return { name: 'same', appearance: 'dark', colors } as unknown as Theme;
}

describe('Write 主题 revision', () => {
  test('同名同外观但语法色变化时 revision 不同', () => {
    const dark = theme({ text: { kind: 'rgb', r: 1, g: 1, b: 1 }, keyword: { kind: 'rgb', r: 2, g: 2, b: 2 } });
    const other = theme({ text: { kind: 'rgb', r: 1, g: 1, b: 1 }, keyword: { kind: 'rgb', r: 3, g: 3, b: 3 } });
    expect(writeThemeRevision(dark)).not.toBe(writeThemeRevision(other));
    expect(writeThemeRevision(dark)).not.toContain('[object Object]');
  });
});
