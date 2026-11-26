# Review Handoff — G0-Bash（第二轮）

## 目标

判断 Bash 的 T0 证据是否足以签署 **G0-Bash**。所有证据在 **固定 Pi 1.6.0**（`/tmp/pi160`，CLI SHA `e79626f2…`）下重跑并记录版本。

## 范围

`tests/pty/bash-cases.py`、`bash-gate.py`、`bash-compressor.py`、`bash-renderer-ab.py`、`bash-slot.py`、`bash-slot-b.py`、`bash-slot-c.py`、`bash-history.py`、`docs/evidence/bash-*.json`、`docs/implementation-status.md` T0-B 行。

## 已验证

- 成功/空/非零/流式；所有 partial 首帧文本为空；final 权威。
- 2100 行：`truncatedBy=lines`，2000 行输出。
- 1500 行 × 42B：`truncatedBy=bytes`，`totalBytes=63000`，`outputBytes=51197`。
- 60KB 单行：`truncatedBy=bytes`，`lastLinePartial=true`。
- 截断 + 执行超时：error，尾部含 `timed out` 诊断；无 truncation details。
- Compressor OFF/ON：ON final 与模型第二轮结果均为 `# shell-compressor` 文本且 details 含 `shellCompressor`；OFF 保留 500 行。
- Gate（非幂等计数）：批准前 0；allow 后恰 1；Esc 拒绝、审批超时、执行超时均 0 且 error。
- `ctx.abort()` 真实 AbortSignal：审批中取消与 allow 后 3000 行输出再取消，均 error、计数 0、无迟到副作用。
- Gate + Compressor 栈 renderer OFF/ON：命令触发真实压缩，各执行 1 次，模型结果逐字一致；`shellCompressor` 1000→153 chars 两侧相同。
- 历史回放：新会话收到 `durationMs`；去掉 `toolResult.durationMs` 的旧格式 fixture 回放为 undefined，正文仍为 `ok\n`。
- Slot：A 否决；B 缺无 result 结构；**C 通过**成功/错误/截断：保留原生 shell/call，`outputPad=1`，命令一次，诊断文本进入 result。

## 已知限制

1. AbortSignal 由测试扩展 `ctx.abort()` 触发，不是真实 ESC 键；取消后的 UI 显示为 `Operation aborted`。
2. Compressor 只校验 `originalChars/compressedChars` 与模型文本，不验证每个内部字段。
3. 尚无 Bash adapter/BashView 产品实现；T3 仍需验证 6/12 行预览、native/UI 截断区分、expanded、resize/cache/history/异常与下游回退。

## 请 reviewer 输出

- T0-B1/B2/B3、Bash slot（候选 C）与 G0-Bash 的 passed/blocked。
- 若可签署，请明确 profile 范围与 T3 必须继续验证的事项；若 blocked，只列最小动作。
