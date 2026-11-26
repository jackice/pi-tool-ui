import { describe, expect, test } from 'vitest';

import { adaptBash } from '../../src/adapters/bash.js';

const base = {
  args: { command: 'pnpm test' },
  options: { isPartial: false, expanded: false },
  context: { isError: false, durationMs: 2800, cwd: '/tmp/project' },
};

describe('Bash 适配', () => {
  test('final 成功映射命令、正文、耗时与 cwd', () => {
    const model = adaptBash({
      ...base,
      result: { content: [{ type: 'text', text: 'a\nb' }], details: undefined },
    });
    expect(model).toMatchObject({
      status: 'success',
      command: 'pnpm test',
      output: 'a\nb',
      durationMs: 2800,
      cwd: '/tmp/project',
      cwdKind: 'execution',
    });
  });

  test('final error 保留诊断，不推断退出码', () => {
    const model = adaptBash({
      ...base,
      options: { isPartial: false, expanded: false },
      context: { isError: true, durationMs: undefined, cwd: '/tmp' },
      result: { content: [{ type: 'text', text: 'command failed' }], details: undefined },
    });
    expect(model.status).toBe('error');
    expect(model.output).toBe('command failed');
    expect(model.durationMs).toBeUndefined();
  });

  test('partial 为空首帧时为 running 且不伪造输出', () => {
    const model = adaptBash({
      ...base,
      options: { isPartial: true, expanded: false },
      result: { content: [], details: undefined },
    });
    expect(model.status).toBe('running');
    expect(model.output).toBe('');
  });

  test('映射 truncation 与 fullOutputPath，忽略非法字段', () => {
    const model = adaptBash({
      ...base,
      result: {
        content: [{ type: 'text', text: 'x' }, { type: 'image' }],
        details: {
          truncation: { totalLines: 2100, outputLines: 2000, totalBytes: 60000, outputBytes: 51200 },
          fullOutputPath: '/tmp/full.log',
        },
      },
    });
    expect(model.truncation).toEqual({ totalLines: 2100, outputLines: 2000, totalBytes: 60000, outputBytes: 51200 });
    expect(model.fullOutputPath).toBe('/tmp/full.log');

    const invalid = adaptBash({
      ...base,
      result: { content: [], details: { truncation: { totalLines: 'x' }, fullOutputPath: 1 } },
    });
    expect(invalid.truncation).toBeUndefined();
    expect(invalid.fullOutputPath).toBeUndefined();
  });

  test('非字符串命令不伪造', () => {
    const model = adaptBash({ ...base, args: { command: 1 }, result: { content: [], details: undefined } });
    expect(model.command).toBeUndefined();
  });
});
