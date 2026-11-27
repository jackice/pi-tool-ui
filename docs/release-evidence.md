# Release evidence — 0.1.0 (Migration profile)

- 包：`@jackice/pi-tool-ui@0.1.0`
- 发布时间：2026-11-26
- 仓库：`git@github.com:jackice/pi-tool-ui.git`，tag `v0.1.0`
- 依赖：`@jackice/pi-ui@0.5.1`；peer 为 Pi 1.6.0 / pi-tui `^1.6.0`
- 发布命令：`npm publish --tag next --access public`
- 验证：`uv run --with pyte python tests/pty/published-verify.py`
  - 干净 `pi install npm:@jackice/pi-tool-ui@0.1.0` 成功
  - 安装树无 `@earendil-works` 实体
  - Edit 卡片等于 `tests/fixtures/migration/edit-native-0.5.1.txt`
  - 文件写入结果为 `alpha\nbeta2\ngamma\n`
- 证据：`docs/evidence/published-install.json`

## 已知偏差

npm 对包的首个版本会自动写入 `latest`，本次 `dist-tags` 为 `{"latest":"0.1.0","next":"0.1.0"}`。尝试 `npm dist-tag rm ... latest` 返回 403，当前 token 无 dist-tag 管理权限，未能只保留 `next`。

影响：`npm install @jackice/pi-tool-ui` 会安装 Migration profile 版本；其默认全部关闭，不会自动接管，但不符合“仅 next”的目标。后续有权限时应移除 `latest` 或发布明确的新版本再调整标签。

## 回滚

- 关闭 `toolUi` 或移除包加载入口，重启恢复原生/下游 renderer。
- 生产配置未在本仓库外自动修改；切换由用户手动执行。

## 0.2.0 preview

- 包：`@jackice/pi-tool-ui@0.2.0`；发布时间 2026-11-27；tag `v0.2.0`；dist-tags `latest=0.1.0`、`next=0.2.0`。
- 依赖：`@jackice/pi-ui@0.8.0`；peer Pi 1.6.0 / pi-tui optional。
- 验证：`published-verify-020.py`：`pi install npm:@jackice/pi-tool-ui@0.2.0` 成功；安装树无 `@earendil-works`；Write/Read 卡片可用。
- 证据：`published-install-020.json`、`startup-rss.json`、`benchmark-views.txt`、`rollback-drill.json`。
- Gate：Bash G3、Write G4、Read G5、G6 已签；T7-01/T7-02/T7-04 通过，T7-03 preview 发布，T7-05 最终评审待办。
- 证据：`benchmark-views.txt`、`rollback-drill.json`、`integration-matrix.json`、`security-stack.json`、`mixed-versions.json`、`pack-artifact.json`、`gallery.txt`。
- 本工作树未执行 npm publish；生产配置未修改。
