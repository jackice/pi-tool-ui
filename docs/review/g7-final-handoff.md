# G7 / T7-05 最终评审交接

## 目标
判定 `pi-tool-ui@0.2.3` preview 是否满足 G7-Release 的当前 profile，或列出最小阻断项。

## Profile
- Bash、Write、Read：G0/G2/G3/G4/G5 已签。
- Edit/Hashline：Migration profile 由 G1 已签；旧扩展不加载。
- 发布标签：npm `next=0.2.3`，`latest=0.1.0`。

## 证据
- 性能：`benchmark-views.txt`、`startup-rss.json`（packed 启动 +1.9ms、RSS +3.73MiB）。
- 回滚：`rollback-drill.json`（单工具/全局/损坏包/移除）。
- 安装：`published-install-023.json`、`pack-artifact.json`。
- 集成/安全：`integration-matrix.json`、`security-stack.json`、`security-compressor.json`、`mixed-versions.json`。
- 视图：`gallery.txt`、各 PTY 证据。
- 解耦：pi-ui 0.8.1 vendored pi-tui ANSI + oracle `ansi-oracle.test.ts`；pi-tui peer optional。

## 已知限制
- T7-02 只做 20 次启动/RSS 与视图预算；未做 1000 历史工具/1000 partial 压力。
- `next` 为 preview；`latest` 仍是 0.1.0；旧 hashline-diff 的迁移回退需用户主动选择。
- vendored ANSI 需在 pi-tui 升级时同步 oracle。
- 已知限制：Gate R2/R3 High/Open；T7-02 压力方法缺口；vendored ANSI 需同步；T7-04 范围已记录。
- 未修改生产配置；未推送 git。

## 问题
1. 是否签 G7/T7-05？若不签，列最小阻断项。
2. 是否有安全/回滚/发布证据不真实或缺失。
