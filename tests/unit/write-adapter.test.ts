import { describe, expect, test } from 'vitest';

import { adaptWrite } from '../../src/adapters/write.js';

const base = {
  args: { path: 'src/app.ts', content: 'alpha\nbeta\n' },
  options: { isPartial: false, expanded: false, argsComplete: true },
  context: { isError: false },
  result: { content: [{ type: 'text', text: 'Wrote 2 lines' }], details: undefined },
};

describe('Write 适配', () => {
  test('final 成功映射 path/content/argsComplete/lineCount', () => {
    const model = adaptWrite(base);
    expect(model).toMatchObject({
      status: 'success',
      path: 'src/app.ts',
      content: 'alpha\nbeta\n',
      argsComplete: true,
      lineCount: 2,
    });
  });

  test('args 不完整时为 streaming，内容取当前快照', () => {
    const model = adaptWrite({
      ...base,
      options: { isPartial: true, expanded: false, argsComplete: false },
      result: { content: [], details: undefined },
    });
    expect(model.status).toBe('streaming');
    expect(model.argsComplete).toBe(false);
    expect(model.content).toBe('alpha\nbeta\n');
  });

  test('CRLF 归一且单尾换行不多计一空行', () => {
    const model = adaptWrite({
      ...base,
      args: { path: 'a.txt', content: 'a\r\nb\r\n' },
    });
    expect(model.content).toBe('a\nb\n');
    expect(model.lineCount).toBe(2);
  });

  test('空内容为 0 行；非字符串内容不伪造', () => {
    expect(adaptWrite({ ...base, args: { path: 'e', content: '' } }).lineCount).toBe(0);
    const invalid = adaptWrite({ ...base, args: { path: 'x', content: { a: 1 } } });
    expect(invalid.content).toBeUndefined();
    expect(invalid.lineCount).toBeUndefined();
  });

  test('final error 保留诊断并标 error', () => {
    const model = adaptWrite({
      ...base,
      context: { isError: true },
      result: { content: [{ type: 'text', text: 'permission denied' }], details: undefined },
    });
    expect(model.status).toBe('error');
    expect(model.notices).toEqual(['permission denied']);
  });
});
