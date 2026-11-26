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
- call：argsComplete=false 时显示路径 + streaming tail；argsComplete=true 清空 call。
- result：最终路径/正文独占；成功 ✓、错误 ✗ 且隐藏正文；失败/取消/历史。
- 高亮：注入 Pi 公开 `highlightCode`，只处理预览行（展开 200 上限），异常/行数不符回退纯文本。
- 刻意不做：增量高亮缓存跨渲染复用；未知语言纯文本。

## 验证
- pi-ui 165 单测；产品 57 单测；typecheck/lint/build。
- write-call-stream、write-view、write-stream、write-product-ab（success/error）、write-history、write-cancel。
- 证据：`write-call-stream.json`、`write-view.json`、`write-stream.json`、`write-product-ab.json`、`write-history.json`、`write-cancel.json`。
