# Review Handoff — G1-Migration

## 目标

判断 `@jackice/pi-tool-ui` 的 Migration profile（Edit/Hashline）是否可签署 **G1-Migration**：独立包、旧行为等价、配置映射、resolver 所有权、下游回退与证据充分性。不评审 Bash/Write/Read（未实现）。

## 范围

- 仓库 `/Users/jackice/dev/src/github.com/jackice/pi-tool-ui`，HEAD `2352122097`。
- 代码：`src/index.ts`、`src/config.ts`、`src/guards.ts`、`src/integration/resolver.ts`、`src/renderers/diff.ts`、`src/adapters/native-edit.ts`、`package.json`、`package-lock.json`、`tsconfig*.json`。
- 测试：`tests/unit/*`、`tests/pty/{migration-parity,export-parity,migration-baseline}.py`、fixtures。
- 文档：`README.md`、`docs/migration.md`、`docs/implementation-status.md`、`docs/compatibility.md`。
- 不在范围：T1-06 发布/生产切换（需用户批准）、Bash/Write/Read、T6 生态回归。

## 计划依据

`docs/implementation-plan.md` §3、§4、§8 T1、§9.3、§12；DAG：G0-Base + T0-02 → T1 → G1。

## 实现摘要

- 新 ESM 包，`pi.extensions` 指向 `dist/index.js`；依赖 `@jackice/pi-ui@0.5.1`，Pi SDK/TUI 为 peer。
- Edit 只替换 `renderResult`；Hashline 额外使用 `self` shell，call 保留。
- 旧 `adaptNativeEdit` 原样迁入；旧 `index.ts` 缓存与回退逻辑迁到 `src/renderers/diff.ts`。
- 配置：默认全关闭；旧 `editDiff.nativeEdit` 与 `PI_HASHLINE_DIFF` 一次性映射；新 `toolUi` 优先并报告冲突；未知键/非法数值拒绝对应工具。
- resolver 每次调用 `next()` 一次；关闭/未知/无下游返回原对象。

## 验证证据

| 命令 | 结果 |
|---|---|
| `npm test` | 19 passed |
| `npm run typecheck` / `npm run build` | 退出 0 |
| `uv run --with pyte python tests/pty/migration-parity.py` | Edit/Hashline 卡片等于 0.5.1 golden；关闭不接管；native-only 一致 |
| `python3 tests/pty/export-parity.py` | 旧新导出 HTML 完全一致；两版均不含工具正文 |
| `python3 tests/pty/migration-baseline.py` | 0.4.2/0.5.1 两版 golden 差异仅为 gutter |
| `npm pack --dry-run` | 仅 dist/README/CHANGELOG/package.json |

## 已知限制（请据此判定）

1. `pi-ui` 使用 0.5.1（`next` tag），不是 npm `latest` 0.4.2；选择理由是与用户当前实际旧 Diff 视觉一致。0.4.2 与 0.5.1 的 gutter 差异已冻结。
2. Hashline `/export` 的 HTML 不含工具正文；旧扩展同样如此，属 Pi 导出模板行为，不是本包引入。计划中“导出保留 call/Diff 正文”在该 Pi 版本不可由 renderer 达成。
3. 生产 `~/.pi/agent` 未修改，未与旧扩展同进程双加载；T1-06 未执行。
4. 未验证真实审批、Shell Compressor、完整生态（属 T6）。
5. `ToolRenderContext` 不是包根导出，renderer 使用结构类型描述所用字段；未 deep import。

## 请 reviewer 输出

- T1-01…T1-05 与 G1-Migration：passed/blocked/pending 与理由（引用文件/行或命令）。
- 是否违反 D01–D10（尤其 D02 只替换 renderer、D03 pi-ui 纯 UI、D05 无参考项目依赖、D08 迁移保持视觉）。
- 若 blocked：最小补齐动作；若通过：明确 migration profile 可发布候选（仍需用户批准切换）。
