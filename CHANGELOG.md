# 0.2.2 (preview erratum)

- 已发布 README 携带已知限制（R2/R3、T7-02/T7-04、vendored ANSI）。
- 对齐 pi-ui 0.8.1 与发布证据。

# 0.2.1 (preview erratum)

- 修正 README/CHANGELOG 依赖与安装说明。
- 补充 LICENSE；随 pi-ui 0.8.1 发布 vendored ANSI 的 NOTICE。

# 0.2.0 (preview)

- Bash slot C：原生 shell/call，`BashView` 命令/输出/截断/全量路径。
- Write：流式参数预览、最终 `WriteView`、Pi 公开 `highlightCode` 有界高亮。
- Read：`ReadView` 行号/范围/截断、Hashline 原文、图片原生回退。
- G6 集成、安全栈、混合 pi-ui、headless/RPC、回滚演练通过；G7 发布待办。
- 依赖 `@jackice/pi-ui@0.7.2`。

# 0.1.0

- Migration profile：接管 `edit` 与 `hashline` 的结果 Diff，行为等价于 `hashline-diff` + `pi-ui@0.5.1`。
- 一次性映射 `editDiff.nativeEdit` 与 `PI_HASHLINE_DIFF` 到 `toolUi`。
- 默认全部关闭；关闭时返回下游 renderer。
