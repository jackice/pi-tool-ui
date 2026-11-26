# Review Handoff — G0-Bash

## 目标

判断 Bash 的 T0 证据是否足以签署 **G0-Bash**：真实 bash 数据、截断、Gate 审批路径、slot 方案。不评审尚未实现的 BashView。

## 范围

- 仓库 `pi-tool-ui`，HEAD `15ff538f78`。
- 证据：`tests/pty/bash-cases.py`、`bash-gate.py`、`bash-slot.py`、`bash-slot-b.py`、`docs/evidence/bash-*.json`、`docs/implementation-status.md` 的 T0-B 行。
- 计划：`docs/implementation-plan.md` §5、§6.1、§8 T0-B、§12。

## 已验证

- 成功：final 文本 `ok\n`，duration 存在。
- 空输出、非零：final 结构已采集。
- 流式：partial ≥1，final 为 `first\nsecond\n`。
- 2100 行：`truncatedBy=lines`，outputLines 2000，totalLines 2100。
- 60KB 输出：`truncatedBy=bytes`，outputBytes 51200。
- 60KB 单行：`truncatedBy=bytes`，lastLinePartial=true。
- Gate：允许后 `chmod` 执行（模式 000）；审批超时返回 Blocked 且模式保持 644。
- Slot：候选 A 被拒（final 后无 call 重绘）；候选 B 通过（call/result 各渲染一段，各一次，共享 state）。

## 已知限制

1. 未单独跑显式 Esc 拒绝、审批期间取消、执行超时。
2. 未单独验证 Shell Compressor 改写后的 final；渲染探针只确认接收宿主 final。
3. Slot B 仅用 marker 组件验证时序/次数，未验证真实边框拼接无重复；需 T3 原型继续验证。
4. 尚无 BashView/adapter 实现。

## 请 reviewer 输出

- T0-B1/B2/B3 与 Bash slot 的 passed/blocked，以及 G0-Bash 是否可签署（可带非阻断限制）。
- 若 blocked，给最小补齐动作。
