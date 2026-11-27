import { initTheme, type Theme } from '@earendil-works/pi-coding-agent';
import { describe, expect, test } from 'vitest';

import { WriteView } from '@jackice/pi-ui';
import { plainTheme } from '@jackice/pi-ui';

import { highlightWrite, writeThemeRevision } from '../../src/renderers/write.js';

function theme(colors: Record<string, unknown>): Theme {
  return { name: 'same', appearance: 'dark', colors } as unknown as Theme;
}

initTheme('dark');

describe('Write 主题 revision', () => {
  test('真实 highlighter 的预览前缀与完整内容 head 一致', () => {
    const full = highlightWrite('const a = 1;\nconst b = 2;', 'typescript');
    const head = highlightWrite('const a = 1;', 'typescript');
    expect(full).toHaveLength(2);
    expect(full[0]).toBe(head[0]);
    expect(full[0]).toContain('\u001b[');
  });

  test('同名同外观但语法色变化会触发 WriteView 重新高亮', () => {
    const colors: Record<string, unknown> = { text: { kind: 'rgb', r: 1, g: 1, b: 1 }, keyword: { kind: 'rgb', r: 2, g: 2, b: 2 } };
    const fake = theme(colors);
    let calls = 0;
    const view = new WriteView(plainTheme(), {
      model: { status: 'success', path: 'a.ts', content: 'const a = 1;', argsComplete: true, lineCount: 1, language: 'typescript' },
      expanded: false,
      config: {
        themeRevision: () => writeThemeRevision(fake),
        highlighter: (code) => { calls += 1; return code.split('\n'); },
      },
    });
    view.render(60);
    expect(calls).toBe(1);
    colors.keyword = { kind: 'rgb', r: 9, g: 9, b: 9 };
    view.render(60);
    expect(calls).toBe(2);
  });

  test('同名同外观但语法色变化时 revision 不同', () => {
    const dark = theme({ text: { kind: 'rgb', r: 1, g: 1, b: 1 }, keyword: { kind: 'rgb', r: 2, g: 2, b: 2 } });
    const other = theme({ text: { kind: 'rgb', r: 1, g: 1, b: 1 }, keyword: { kind: 'rgb', r: 3, g: 3, b: 3 } });
    expect(writeThemeRevision(dark)).not.toBe(writeThemeRevision(other));
    expect(writeThemeRevision(dark)).not.toContain('[object Object]');
  });
});
