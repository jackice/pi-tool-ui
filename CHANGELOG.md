# Unreleased

- 新增 Bash slot C：保留原生 shell/call，使用 `BashView` 渲染命令、输出、截断与全量路径。
- 新增 Write 参数流式预览与 Read `ReadView`（预览）。
- 依赖 `@jackice/pi-ui@0.6.7`。

# 0.1.0

- Migration profile：接管 `edit` 与 `hashline` 的结果 Diff，行为等价于 `hashline-diff` + `pi-ui@0.5.1`。
- 一次性映射 `editDiff.nativeEdit` 与 `PI_HASHLINE_DIFF` 到 `toolUi`。
- 默认全部关闭；关闭时返回下游 renderer。
