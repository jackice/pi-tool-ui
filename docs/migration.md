# 迁移映射

旧 `hashline-diff` 的实际行为：

| 来源 | 条件 | 目标 |
|---|---|---|
| `editDiff.nativeEdit` | 严格 `true` | `toolUi.tools.edit.enabled` |
| `PI_HASHLINE_DIFF` | 值不等于字符串 `0`（未设置也算启用） | `toolUi.tools.hashline.enabled` |
| 以上两者 | 逻辑或 | `toolUi.enabled` |

未交付工具（`bash`、`write`、`read`）始终维持默认关闭。

## 优先级与冲突

1. 存在 `toolUi` 时使用新配置；源标记为 `new`。
2. 若同时存在旧配置且映射值不同，产生诊断并保留新值，不静默改配置。
3. 不存在 `toolUi` 且存在任一旧来源时使用旧映射；源标记为 `legacy`。
4. 两者都不存在时保持默认全关闭；源标记为 `default`。

## 显式迁移命令

旧安装若既没有 `editDiff` 也没有设置 `PI_HASHLINE_DIFF`，自动检测无法区分“全新安装”和“沿用旧默认”。此时使用：

- `/tool-ui-migrate` 或 `/tool-ui-migrate dry`：预览将写入的 edit/hashline/enabled 值，不落盘。
- `/tool-ui-migrate force`：确认后备份 `settings.json`，再用临时文件 + rename 原子写入 `toolUi`。

全新安装不运行该命令，保持全部关闭。若检测到 `extensions/hashline-diff` 仍存在，启动会禁用本包并提示，避免双加载。

## 校验

- `enabled` 必须是布尔值；顶层无效则全部关闭。
- 未知键拒绝对应工具的整段配置，其他工具保留。
- 预览行数必须是 1..100 的有限整数。
- 缺省字段使用冻结默认值，不做字符串隐式转换。
- ANSI 安全过滤与预算是运行时行为，不受配置关闭。

## 切换步骤

1. 备份 `~/.pi/agent/settings.json` 与 `~/.pi/agent/extensions/hashline-diff/`。
2. 记录当前 `PI_HASHLINE_DIFF` 有效值与 `editDiff.nativeEdit`。
3. 退出 Pi，把旧扩展移出发现范围。
4. 安装 `@jackice/pi-tool-ui`，按上表写入配置。
5. 重启；确认只有一个 resolver owner，且 Edit/Hashline 卡片与迁移前一致。

## 回滚

- 一级：关闭对应工具或 `toolUi.enabled`，重启恢复下游 renderer。
- 二级：移除新包加载入口，恢复旧扩展、旧配置与锁文件，重启。
- 未安装过旧扩展的环境只回退到原生 Pi，不自动安装旧包。

## 已验证的视觉差异

`pi-ui@0.4.2`（旧锁文件）与 `0.5.1`（旧扩展实际安装）行号 gutter 不同：0.5.x 对 context/removed 行去重。迁移以 0.5.1 golden 为准；该差异不是新包引入。golden 在 `tests/fixtures/migration/`。
