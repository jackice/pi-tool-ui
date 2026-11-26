# Review Handoff — T0 / G0-Base

## 目标

判断 `pi-tool-ui` 的 T0 公共证据是否足以关闭 **G0-Base**：真实 Pi 1.6.0 下的公共 SDK、隔离测试设施、包加载与 renderer 机制。只审证据与测试，不评审产品 UI（尚未实现）。

## 范围

- 仓库：`/Users/jackice/dev/src/github.com/jackice/pi-tool-ui`，提交 `4ed30dad9b`。
- 评审文件：`docs/implementation-plan.md`、`docs/compatibility.md`、`docs/implementation-status.md`、`tests/pty/*.py`、`tests/pty/{probe,peer}.ts`。
- 任务：T0-01、T0-03、T0-04、T0-05、T0-I 及 G0-Base。
- 不在范围：T0-02、T0-B*/W*/R*/RH（尚未执行）、T1 迁移实现、任何生产配置或发布。

## 计划依据

- `docs/implementation-plan.md` §2、§5、§8 T0、§12 门禁定义；原始计划亦在 `dotfiles/docs/pi-tool-ui-implementation-plan-v1.0.md`。
- 计划要求：G0-Base 仅使用 T0-01、T0-03..05、T0-I 的公共 SDK、测试设施和包加载证据；每项需运行证据与独立 Reviewer 结论。

## 实现摘要

- 新增隔离 PTY 探针（`tests/pty/smoke.py` + `terminal.py`），用本地 faux provider 执行真实 Pi 的 `read`。
- 验证：resolver 顺序、`next()` 回退、共享 `context.state`、两 slot 组件、`outputPad=1`、Ctrl+O 展开、历史回放、`/reload`、进程内主题切换、结果构造异常回退、无 UI 路径。
- 打包：临时 tarball + 干净 npm 安装 + 受管 `pi install`（参考包）验证无第二套 Pi runtime；公开 `highlightCode`/`getLanguageFromPath` 实测。
- 完整栈：复制全部本地扩展（移除旧 Diff），生产 npm 树只读引用，离线启动并完成一次 TUI Read。
- 有意未做：不改生产 `~/.pi/agent`；不发布；不实现 T1+；未验证真实审批/Compressor 行为；旧 Diff 视觉基线未采集。

## 验证证据

| 命令 | 结果 |
|---|---|
| `python3 tests/pty/smoke.py` | 通过；详见 `docs/implementation-status.md` “Resolver 顺序实测”及历史/主题段落 |
| `python3 tests/pty/package-smoke.py` | 通过；干净安装加载 `dist/index.js` |
| `python3 tests/pty/managed-install-smoke.py` | 通过；受管安装、核心栈 print/TUI、下游保留 |
| `python3 tests/pty/full-stack-smoke.py` | 通过；完整本地扩展栈离线启动与 TUI Read |
| `git log --oneline` | `4ed30da`…`d02227b`，均为 test/docs 提交 |

## 已知缺口（请据此判断门禁是否可关闭）

1. `docs/compatibility.md` 记录的固定 GitHub commit 未与安装产物逐文件核对；`gitHead` 缺失。
2. T0-05 的“实际迁移候选包安装”未做（尚无候选包）；参考包受管安装已验证 peer 处理。
3. Hashline 的 `pi install` 两次超时，核心/完整栈使用本机固定版本只读副本。
4. 未验证真实 Bash 审批、Shell Compressor 改写、生产开关 `toolUi` 时序。
5. `Component.render(width)` 抛错未被宿主自动捕获的行为未验证；仅验证接入层回退。
6. 所有动态证据尚未采集截图/transcript 归档，只有脚本断言与状态文档。

## 请 reviewer 输出

- 逐项判断 T0-01/03/04/05/I 与 G0-Base：passed / blocked / pending，并给出理由。
- 若 blocked，列出最小补齐动作。
- 检查是否有把静态证据当运行证据、或超出计划范围接管的行为。
