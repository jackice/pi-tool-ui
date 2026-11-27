# @jackice/pi-tool-ui

Pi 工具结果卡片。保留原生执行、权限与工具 schema，只替换展示；`edit`/`hashline` 为 Migration profile，Bash/Write/Read 为独立预览。

## 状态

- 默认全部关闭；全新安装不改变原生行为。
- 存在 `editDiff.nativeEdit` 或 `PI_HASHLINE_DIFF` 时自动迁移旧配置；两者都没有的旧安装用 `/tool-ui-migrate` 显式预览/应用。见 [docs/migration.md](docs/migration.md)。
- Bash 已交付；Write 参数流式预览已接入，highlight 与 failure/cancel 矩阵未完成；Read 预览已接入，门禁复审中。

## 安装

```bash
pi install npm:@jackice/pi-tool-ui
```

依赖 `@jackice/pi-ui@0.7.2`。Pi 宿主提供 `@earendil-works/pi-coding-agent` 与 `@earendil-works/pi-tui`，不要自行安装第二套。

## 配置

```json
{
  "toolUi": {
    "enabled": true,
    "tools": {
      "edit": { "enabled": true },
      "hashline": { "enabled": true }
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
