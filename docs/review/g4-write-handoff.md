# G4-Write 评审交接

## 目标
验证 Write 接管只改变展示，不改变文件字节、args、错误、执行次数；判定 T4-03/T4-05 与 G4-Write 是否可签署。

## 范围
- `src/adapters/write.ts`、`src/renderers/write.ts`、`src/integration/resolver.ts`
- pi-ui `src/views/write.ts`、`src/components/code-block.ts`（0.7.0）
- `tests/unit/write-adapter.test.ts`、`tests/unit/resolver.test.ts`
- `tests/pty/write-*.{py,ts}`、`docs/evidence/write-*.json`
- `docs/implementation-status.md`

Out of scope：Bash/Read 门禁、发布、生产切换。

## 实现摘要
- call：流式（isPartial）显示路径 + tail；完成/历史（argsComplete 或 !isPartial）只保留 `write <path>` 一行。
- result：最终正文独占（路径在 call 行）；成功 ✓、错误 ✗ 且隐藏正文；失败/取消/历史。
- 高亮：注入 Pi 公开 `highlightCode`，折叠只处理 6/12 行，展开 200 上限；输入上限 10k 行/256 KiB；组件缓存；异常/行数不符回退纯文本。
- 刻意不做：跨组件/跨会话高亮缓存；未知语言由 highlighter 回退纯文本。

## 验证
- pi-ui 165 单测；产品 57 单测；typecheck/lint/build。
- write-call-stream、write-view、write-stream、write-product-ab（success/error）、write-history、write-cancel。
- 证据：`write-call-stream.json`、`write-view.json`、`write-stream.json`、`write-product-ab.json`、`write-history.json`、`write-cancel.json`。
