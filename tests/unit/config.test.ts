import { describe, expect, test } from 'vitest';

import { DEFAULT_CONFIG, mapLegacyConfig, parseToolUiConfig } from '../../src/config.js';

describe('默认配置', () => {
  test('全新安装全部关闭', () => {
    const result = mapLegacyConfig({});
    expect(result.config).toEqual(DEFAULT_CONFIG);
    expect(result.config.enabled).toBe(false);
    expect(Object.values(result.config.tools).every((tool) => !tool.enabled)).toBe(true);
  });
});

describe('旧配置映射', () => {
  test('nativeEdit 与 Hashline 默认开启映射为逻辑或', () => {
    const result = mapLegacyConfig({ editDiff: { nativeEdit: true } });
    expect(result.source).toBe('legacy');
    expect(result.config.tools.edit.enabled).toBe(true);
    expect(result.config.tools.hashline.enabled).toBe(true);
    expect(result.config.enabled).toBe(true);
    expect(result.config.tools.bash.enabled).toBe(false);
  });

  test('PI_HASHLINE_DIFF=0 只关闭 Hashline', () => {
    const result = mapLegacyConfig({ editDiff: { nativeEdit: true }, envHashline: '0' });
    expect(result.config.tools.edit.enabled).toBe(true);
    expect(result.config.tools.hashline.enabled).toBe(false);
    expect(result.config.enabled).toBe(true);
  });

  test('两个来源都关闭时全局开关为 false', () => {
    const result = mapLegacyConfig({ envHashline: '0' });
    expect(result.config.tools.edit.enabled).toBe(false);
    expect(result.config.tools.hashline.enabled).toBe(false);
    expect(result.config.enabled).toBe(false);
  });

  test('显式迁移上下文在无旧键时保留 Hashline 默认', () => {
    const result = mapLegacyConfig({ legacy: true });
    expect(result.source).toBe('legacy');
    expect(result.config.tools.hashline.enabled).toBe(true);
    expect(result.config.tools.edit.enabled).toBe(false);
    expect(result.config.enabled).toBe(true);
  });

  test('nativeEdit 非严格 true 不启用 Edit', () => {
    const result = mapLegacyConfig({ editDiff: { nativeEdit: 'true' } });
    expect(result.config.tools.edit.enabled).toBe(false);
  });
});

describe('新配置校验', () => {
  test('已有 toolUi 优先并报告与旧配置冲突', () => {
    const result = mapLegacyConfig({
      toolUi: { enabled: true, tools: { edit: { enabled: false }, hashline: { enabled: true } } },
      editDiff: { nativeEdit: true },
    });
    expect(result.source).toBe('new');
    expect(result.config.tools.edit.enabled).toBe(false);
    expect(result.config.tools.hashline.enabled).toBe(true);
    expect(result.diagnostics.some((item) => item.includes('edit'))).toBe(true);
  });

  test('顶层类型无效则全部关闭', () => {
    const diagnostics: string[] = [];
    const config = parseToolUiConfig({ enabled: 'yes', tools: { edit: { enabled: true } } }, diagnostics);
    expect(config.enabled).toBe(false);
    expect(config.tools.edit.enabled).toBe(false);
    expect(diagnostics).toHaveLength(1);
    expect(parseToolUiConfig('yes', []).enabled).toBe(false);
  });

  test('未知键拒绝对应工具但保留其他工具', () => {
    const diagnostics: string[] = [];
    const config = parseToolUiConfig({
      enabled: true,
      tools: { edit: { enabled: true, mystery: 1 }, hashline: { enabled: true } },
    }, diagnostics);
    expect(config.tools.edit.enabled).toBe(false);
    expect(config.tools.hashline.enabled).toBe(true);
    expect(diagnostics).toHaveLength(1);
  });

  test('preview 必须是 1..100 的有限整数', () => {
    const diagnostics: string[] = [];
    const config = parseToolUiConfig({
      tools: {
        bash: { enabled: true, output: { previewRows: 101 } },
        write: { enabled: true, previewLines: 0 },
        read: { enabled: true, previewLines: 1.5 },
      },
    }, diagnostics);
    expect(config.tools.bash.enabled).toBe(false);
    expect(config.tools.write.enabled).toBe(false);
    expect(config.tools.read.enabled).toBe(false);
    expect(diagnostics).toHaveLength(3);
  });

  test('缺省字段使用冻结默认值且不做字符串转换', () => {
    const config = parseToolUiConfig({ tools: { bash: { enabled: true } } }, []);
    expect(config.tools.bash).toEqual({
      enabled: true,
      command: { highlight: true, previewRows: 6 },
      output: { previewRows: 12, ansi: true, showTruncation: true, showFullOutputPath: true },
      showDuration: true,
      showCwd: false,
    });
  });
});
