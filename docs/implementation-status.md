# 实施状态

当前批次：T0 起步；未改生产设置、未发布、未进入 renderer 产品实现。基线和指纹见 [compatibility.md](compatibility.md)。

| ID | 状态 | 证据与缺口 |
|---|---|---|
| T0-01 | passed | 已记录本机 CLI/SDK 指纹、安装版本、包导出键与根导出差异；固定 commit 的 `ToolRenderContext` 文本与安装声明逐项一致。构建产物整体对应关系未证，已记入 compatibility。 |
| T0-02 | passed | 旧源码、配置分支与指纹已冻结；真实 PTY 冻结原生 Edit 与 Hashline 的 0.4.2/0.5.1 卡片 golden，见 `tests/fixtures/migration/`。Hashline `/export` HTML 对账归 T1-02。 |
| T0-03 | running | `python3 tests/pty/smoke.py` 在隔离 HOME、Agent dir、临时 cwd 和空白 session 中成功执行真实 Pi 1.6.0；本地 SDK faux provider 发起一次 `read`，屏幕出现 `PROBE_DONE`，无真实认证或付费模型。 |
| T0-04 | running | 已实测行级 state、slot 组件复用、`outputPad=1`、展开、无 UI、resolver 顺序、下游回退、历史回放、`/reload`、结果构造异常回退及进程内主题切换。 |
| T0-05 | running | 已验证公开高亮、宽度、ESM 打包入口和 Pi 受管安装的 peer 处理；宿主 SDK/TUI 与 `pi-ui@0.4.2` 可用。仍待实际迁移候选包的安装验证。 |
| T0-I | running | 隔离核心栈与完整用户扩展栈均启动成功；完整栈的 TUI 读取已进入 renderer。生产开关与真实审批路径仍待独立验收。 |
| T0-RH | running | 范围改写、错误跳过、截断与 details 共存已实测；待历史与图片路径。 |
| T0-B1…B3、T0-W1…W2、T0-R1…R2 | pending | 公共 Read 探针不替代各工具的专用探针。 |
| G0-Base、G0-Bash、G0-Write、G0-Read、G0-ReadHash（可选） | pending | G0-Base 已提交独立评审请求；Bash/Write/Read 未启动。 |
| G1-Migration、G2-Shared（Bash/Write/Read）、G3-Bash、G4-Write、G5-Read、G5-ReadHash（可选）、G6、G7 | pending | 未到进入条件。 |

### Resolver 顺序实测

`python3 tests/pty/smoke.py`：两种显式 `-e` 顺序中，Read 的两个 resolver 均按加载顺序进入，各一次；双方都覆盖结果时，先加载者的结果出现在屏幕。探针排在前面但返回原对象时，屏幕保留后加载的自定义 `PEER_RESULT`。这仅证明显式加载的探针组合，不证明生产栈不存在同名竞争。

历史回放：以 `--print --session` 生成真实会话，修改临时目录中的原文件，再用 PTY 打开同一会话而不提交新提示。renderer 收到保存的旧正文和 final，新进程首次 result 未复用旧组件；无 Read `tool_call` 事件。

历史会话中通过 PTY 输入 `/reload`，等待 Pi 自身的重载完成提示。记录到第二次 `session_start` 及新的 result 组件，保存的 final 正文未改变，也未出现 Read `tool_call`。

探针注入结果构造异常，接入层捕获后调用原 `renderResult`；PTY 显示自定义下游 `PEER_RESULT`，Read 仅触发一次。该结果不证明宿主自动捕获渲染异常，也不覆盖 `Component.render(width)` 抛错。

Pi 分别以 `--use-theme dark/light` 启动；公开 `getLanguageFromPath` 将 `.ts` 识别为 TypeScript，`highlightCode` 的 SGR 样式随主题变化，去除 SGR 后两次都保留完整源码。

在同一 Pi 进程通过公开 `ctx.ui.setTheme('light')` 切换主题，随后以 Ctrl+O 重新展开工具行。高亮输出从 dark 基线变为 light 基线，Read 未重跑。未据此假定主题变更本身一定触发 renderer 回调或 Theme 实例一定更换。

打包探针：`python3 tests/pty/package-smoke.py` 创建最小 tarball，用 `npm install --legacy-peer-deps` 装入隔离目录，经 `settings.json` 的本地 package 发现入口。安装树无第二套 Pi SDK/TUI；Pi 加载 manifest 的 `dist/index.js`，可调用宿主语言识别、宽度函数、TUI Text，并导入 `pi-ui@0.4.2` 的 EditView。首次 `--omit=peer` 安装超时，不能据此认定该模式不兼容。未验证 `pi install`，探针不等同于发布候选。

受管安装探针：`python3 tests/pty/managed-install-smoke.py` 在空白 HOME/Agent dir 使用 `pi install npm:@jackice/pi-session-todo@0.1.2`。安装树只有扩展与 `pi-ui@0.4.2`，未出现独立 Pi SDK/TUI；重启 CLI 后实际注册 `--session-todo-hide-ms`。此证据覆盖已发布参考包的受管安装，不替代 `pi-tool-ui` 候选包验收。

核心栈探针共装 Hashline 0.1.2、Approval 0.1.6、TODO 0.1.2、Prompt 0.2.1 和本地 Shell Compressor，排除旧 Diff。Hashline 受管安装两次超时，原因未确定；核心栈改用本机固定版本依赖的只读副本，在临时 HOME、Agent dir 和 cwd 中启动。TODO 与 Approval 注册了 CLI 参数，确定性 provider 在 print 模式下完成一次 Read，未进入 renderer。未覆盖完整用户扩展、真实审批或 Compressor 的 Bash 改写。

核心栈的真实 PTY 也已验证：Hashline 0.1.2 改写后的 Read final（路径锚点与 `1:` 正文）到达 renderer，Read 只调用一次。另一次运行中前置探针透传，屏幕保留后置自定义 renderer，未显示探针结果。此证据只覆盖核心栈与一条 Hashline 改写路径，不关闭 T0-RH。

完整栈探针：`python3 tests/pty/full-stack-smoke.py` 复制本机全部本地扩展（移除旧 Diff），配置 13 个已安装包指向生产 npm 树的只读路径，在临时 HOME/Agent dir 启动。离线 `--help` 无加载失败，TODO、Approval、Handoff 的 CLI 参数均出现；`--print` 与真实 PTY 各执行一次 Read，PTY 中探针 renderer 收到 Hashline 改写后的 final。生产 npm 树只读引用，未验证真实审批、Compressor 改写或启用 `toolUi` 后的配置生命周期。

### 旧 Diff 视觉基线（T0-02）

`uv run --with pyte python tests/pty/migration-baseline.py` 用旧扩展源码、`@jackice/hashline@0.1.2` 与本机两份 `pi-ui`（0.4.2、0.5.1）建立隔离 Agent dir，真实 PTY 分别执行一次原生 `edit` 和一次 `hashline`，用 pyte 还原最终帧并只保留卡片区域；耗时、路径与边框长度已归一化。golden 位于 `tests/fixtures/migration/`。

结果：两种工具的卡片在 0.5.1 下完全一致；0.4.2 与 0.5.1 的差异仅为行号 gutter——0.5.x 对 context/removed 行去重，0.4.2 同时显示新旧两列行号。其余标题、摘要、正文、边框一致。当前用户实际运行 0.5.1，因此迁移 parity 以 0.5.1 golden 为准，0.4.2 作为锁文件基线保留。该差异不是本次迁移引入。

### Hashline Read 实测（T0-RH）

`python3 tests/pty/hashline-read-cases.py` 将 `@jackice/hashline@0.1.2` 放入隔离 Agent dir，用真实 PTY 执行三种 Read；原始结果保存在 `docs/evidence/hashline-read-cases.json`。

- `offset=5, limit=3`：正文改为 `[long.txt#TAG]` 加 `5:line 5`…`7:line 7`，编号来自真实文件行号。
- 文件不存在：保留原生错误文本，不写入锚点。
- 2101 行文件：正文含 `1:`…`2000:line 2000`、原生 `[Showing lines 1-2000 of 2101. Use offset=2001 to continue.]`、空行与 Hashline 两行提示；`details.truncation` 仍在，未被子类改写清除。

原生 `[Showing lines …]` 与普通源文件文本同形，通用 renderer 无法仅凭外观安全剥离；后续 Read adapter 必须按 §6.3/§6.4 的证据规则降级，不据文本形状推断来源。

下一步审查 G0-Base。
