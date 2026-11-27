# @jackice/pi-tool-ui

Pi 工具结果卡片。保留原生执行、权限与工具 schema，只替换展示；`edit`/`hashline` 为 Migration profile，Bash/Write/Read 为独立预览。

## 状态

- 默认全部关闭；全新安装不改变原生行为。
- 存在 `editDiff.nativeEdit` 或 `PI_HASHLINE_DIFF` 时自动迁移旧配置；两者都没有的旧安装用 `/tool-ui-migrate` 显式预览/应用。见 [docs/migration.md](docs/migration.md)。
- Bash、Write、Read 已通过各自 G0/G2/G3/G4/G5 与 G6 集成评审；默认关闭，需显式启用。

## 已知限制

- 发布标签：`next=0.2.3`，`latest=0.1.0`；按 `@next` 安装。
- Approval Gate 继承 R2/R3（High、Open，见 `pi-approval-gate/docs/security-review.md`）；产品不扩大其范围。
- `pi-ui` 的 ANSI 工具 vendored 自 pi-tui 1.6.0；升级 pi-tui 时需同步 oracle。pi-ui 根 `approval` 子路径仍需要宿主 pi-tui。
- T7-02 已测 20 次启动/RSS 与 100/1000/10000 行渲染；未做 1000 次 partial/1000 历史工具行压力。
- T7-04 覆盖 Bash/Write/Read 的回滚；Edit/Hashline 迁移回退需用户主动选择旧扩展。

## 安装

```bash
pi install npm:@jackice/pi-tool-ui@next
```

依赖 `@jackice/pi-ui@0.8.1`。Pi 宿主提供 `@earendil-works/pi-coding-agent` 与 `@earendil-works/pi-tui`，不要自行安装第二套。

## 配置

```json
{
  "toolUi": {
    "enabled": true,
    "tools": {
      "edit": { "enabled": true },
      "hashline": { "enabled": true },
      "bash": { "enabled": true },
      "write": { "enabled": true },
      "read": { "enabled": true }
    }
  }
}
```

`toolUi.enabled` 是总开关。配置在启动时读取；修改后需要重启或 `/reload`。

## 从 hashline-diff 迁移

- `editDiff.nativeEdit === true` → `tools.edit.enabled`
- `PI_HASHLINE_DIFF !== "0"` → `tools.hashline.enabled`（未设置视为启用）
- 两者逻辑或 → `toolUi.enabled`
- 已存在 `toolUi` 时新配置优先，并报告与旧值的冲突

迁移前备份 `~/.pi/agent/settings.json` 与旧扩展目录。不要与旧 `hashline-diff` 在同一进程同时加载。

## 开发

```bash
npm install --legacy-peer-deps
npm test
npm run typecheck
npm run build
uv run --with pyte python tests/pty/migration-parity.py
```
