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
- Gate + Compressor 栈 renderer OFF/ON：各执行 1 次，模型第二轮 tool result 逐字一致。
- 历史回放：renderer 收到 `durationMs`（4ms）与 `ok\n`。
- Slot：A 否决（final 后无 call 重绘）；B 仅有 marker 与边框，缺无 result 结构；**C 通过**：保留原生 shell/call，仅替换 result，命令仅出现一次，无 result 时原生 call 结构完整。

## 已知限制

1. 执行取消未单独用 AbortSignal 触发，使用执行超时覆盖；approval 期间取消用 Esc 覆盖。
2. 历史 `durationMs` 缺失样本无法由 Pi 1.6.0 产生；renderer 端 undefined 分支仅由代码路径保证。
3. 截断后取消未单列。
4. Compressor 的 `details.shellCompressor` 仅验证存在，未验证每个字段语义。
5. 尚无 Bash adapter/BashView 产品实现；T3 仍需验证 6/12 行预览、native/UI 截断区分、expanded、resize/cache/history/异常与下游回退。

## 请 reviewer 输出

- T0-B1/B2/B3、Bash slot（候选 C）与 G0-Bash 的 passed/blocked。
- 若可签署，请明确 profile 范围与 T3 必须继续验证的事项；若 blocked，只列最小动作。
