import { describe, expect, test } from 'vitest';

import { adaptRead } from '../../src/adapters/read.js';

const base = {
  args: { path: 'src/app.ts' },
  options: { isPartial: false, expanded: false },
  context: { isError: false },
  result: { content: [{ type: 'text', text: 'alpha\nbeta\ngamma\n' }], details: undefined },
};

describe('Read 适配', () => {
  test('默认 offset 从 1 开始编号并识别代码', () => {
    const model = adaptRead(base);
    expect(model.status).toBe('success');
    expect(model.contentKind).toBe('code');
    expect(model.lines.map((line) => [line.number, line.text])).toEqual([[1, 'alpha'], [2, 'beta'], [3, 'gamma']]);
  });

  test('正整数 offset 决定起始行号', () => {
    const model = adaptRead({ ...base, args: { path: 'src/app.ts', offset: 5, limit: 3 } });
    expect(model.requestedOffset).toBe(5);
    expect(model.requestedLimit).toBe(3);
    expect(model.lines.map((line) => line.number)).toEqual([5, 6, 7]);
  });

  test('非法 offset 不推断行号', () => {
    const model = adaptRead({ ...base, args: { path: 'a.ts', offset: 1.5 } });
    expect(model.lines.every((line) => line.number === null)).toBe(true);
    expect(model.requestedOffset).toBeUndefined();
  });

  test('Hashline 锚点保留原文且不额外编号', () => {
    const model = adaptRead({
      ...base,
      result: { content: [{ type: 'text', text: '[a.ts#D8C1]\n1:alpha\n2:beta' }], details: undefined },
    });
    expect(model.source).toBe('hashline');
    expect(model.lines).toEqual([]);
    expect(model.rawFallback).toContain('[a.ts#D8C1]');
  });

  test('图片块识别为 image 且不编号', () => {
    const model = adaptRead({
      ...base,
      result: { content: [{ type: 'text', text: 'Read image file [image/png]' }, { type: 'image' }], details: undefined },
    });
    expect(model.contentKind).toBe('mixed');
    expect(model.lines).toEqual([]);
    expect(model.rawFallback).toBe('Read image file [image/png]');
  });

  test('错误保留诊断，firstLineExceedsLimit 不提供源码正文', () => {
    expect(adaptRead({ ...base, context: { isError: true }, result: { content: [{ type: 'text', text: 'EACCES' }], details: undefined } }).status).toBe('error');
    const limited = adaptRead({
      ...base,
      result: { content: [{ type: 'text', text: 'x'.repeat(20) }], details: { truncation: { firstLineExceedsLimit: true, totalLines: 1, outputLines: 0 } } },
    });
    expect(limited.lines).toEqual([]);
    expect(limited.truncation?.firstLineExceedsLimit).toBe(true);
  });

  test('Markdown 标记为 markdown-source 并映射 truncation', () => {
    const model = adaptRead({
      ...base,
      args: { path: 'notes.md' },
      result: { content: [{ type: 'text', text: '# Title\n' }], details: { truncation: { totalLines: 2100, outputLines: 2000, truncatedBy: 'lines' } } },
    });
    expect(model.contentKind).toBe('markdown-source');
    expect(model.truncation).toEqual({ totalLines: 2100, outputLines: 2000, by: 'lines' });
  });
});
