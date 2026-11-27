# T6-03 安全评审交接

## 目标
确认 pi-tool-ui 的 Bash 接管只改变展示，不扩大、绕过或削弱 Approval Gate、uv guard、Shell Compressor；判定 T6-03 是否可签。

## 范围
- `src/renderers/bash.ts`、`src/integration/resolver.ts`、`src/index.ts`、`src/config.ts`
- `tests/pty/bash-gate.py`、`bash-compressor.py`、`bash-abort.py`、`integration-matrix.py`
- `docs/evidence/bash-gate.json`、`bash-compressor.json`、`bash-abort.json`
- `/Users/jackice/dev/src/github.com/jackice/pi-approval-gate`（只读）
- `/Users/jackice/dev/src/github.com/jackice/dotfiles/pi/.pi/agent/extensions/bash-guard.ts`（只读）

## 实现摘要
- 产品不注册 Bash 工具、不改 spawn/approval/compressor；仅替换 `bash.renderResult`，raw fallback。
- `user_bash`/Gate 自有流程不被接管。
- 产品与 Gate/Compressor 分别由宿主加载；无全局执行缓存。

## 验证
- Bash G2/G3 已签；gate allow/deny/timeout/cancel、compressor 真压缩、abort 计数 0 有证据。
- `integration-matrix.py`：产品 ON/OFF 下 bash content/details/files 一致，各执行一次。
- 缺口：尚无“Gate 与产品同时 ON”的专门 PTY 证据；`bash-gate.py` 未加载产品。

## 问题
1. 是否存在产品导致 Gate 被绕过/多执行/少执行的代码路径？
2. 产品渲染或缓存是否能暴露未批准命令输出、错误展示批准状态？
3. 是否需要补 Gate+产品同开 PTY 才能签 T6-03？
