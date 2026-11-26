import { describe, expect, test } from 'vitest';

import { adaptNativeEdit } from '../../src/adapters/native-edit.js';

const timing = { toolCallId: 'call-1', durationMs: 12 };
const patch = [
  '--- notes.txt',
  '+++ notes.txt',
  '@@ -1,3 +1,3 @@',
  ' alpha',
  '-beta',
  '+beta2',
  ' gamma',
].join('\n');
const args = { path: 'notes.txt' };

describe('原生 Edit 适配', () => {
  test('把单文件 unified diff 转为带行号的模型', () => {
    const model = adaptNativeEdit({ patch }, args, timing)!;
    expect(model.toolCallId).toBe('call-1');
    expect(model.durationMs).toBe(12);
    expect(model.files[0]?.path).toBe('notes.txt');
    expect(model.files[0]?.hunks[0]?.lines.map((line) => [line.kind, line.content])).toEqual([
      ['context', 'alpha'],
      ['removed', 'beta'],
      ['added', 'beta2'],
      ['context', 'gamma'],
    ]);
    expect(model.files[0]?.additions).toBe(1);
    expect(model.files[0]?.deletions).toBe(1);
  });

  test('多文件或不同文件头的补丁交还原生渲染', () => {
    expect(adaptNativeEdit({ patch: '--- a\n+++ b\n@@ -1 +1 @@\n-x\n+y' }, args, timing)).toBeUndefined();
    expect(adaptNativeEdit({ patch }, { path: '' }, timing)).toBeUndefined();
  });

  test('无改动或畸形 hunk 不伪造 Diff', () => {
    expect(adaptNativeEdit({ patch: '--- a\n+++ a\n@@ -1 +1 @@\n x' }, { path: 'a' }, timing)).toBeUndefined();
    expect(adaptNativeEdit({ patch: '--- a\n+++ a\n@@ nope\n' }, { path: 'a' }, timing)).toBeUndefined();
  });

  test('非法 details 或参数保持未定义', () => {
    expect(adaptNativeEdit(null, args, timing)).toBeUndefined();
    expect(adaptNativeEdit({ patch: 1 }, args, timing)).toBeUndefined();
    expect(adaptNativeEdit({ patch }, null, timing)).toBeUndefined();
  });
});
