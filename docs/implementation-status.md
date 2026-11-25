# 实施状态

当前批次：T0 起步；未改生产设置、未发布、未进入 renderer 产品实现。基线和指纹见 [compatibility.md](compatibility.md)。

| ID | 状态 | 证据与缺口 |
|---|---|---|
| T0-01 | running | 已记录本机 CLI/SDK 指纹、安装版本和包导出键；待核对公开源码树、实际解析指纹与全部根导出。 |
| T0-02 | running | 已登记旧入口、源码指纹、配置分支及锁与实际依赖漂移；待冻结匿名旧视觉 fixture、HTML 及许可归属。 |
| T0-03 | running | `python3 tests/pty/smoke.py` 在隔离 HOME、Agent dir、临时 cwd 和空白 session 中成功执行真实 Pi 1.6.0；本地 SDK faux provider 发起一次 `read`，屏幕出现 `PROBE_DONE`，无真实认证或付费模型。 |
| T0-04 | running | 已实测行级 state、slot 组件复用、`outputPad=1`、展开、无 UI、resolver 顺序、下游回退、历史回放、`/reload`、结果构造异常回退及进程内主题切换。 |
| T0-05 | running | 已验证公开高亮、宽度、ESM 打包入口和 Pi 受管安装的 peer 处理；宿主 SDK/TUI 与 `pi-ui@0.4.2` 可用。仍待实际迁移候选包的安装验证。 |
| T0-I、T0-B1…B3、T0-W1…W2、T0-R1…R2、T0-RH | pending | 公共 Read 探针不替代各工具的专用探针。 |
| G0-Base、G0-Bash、G0-Write、G0-Read、G0-ReadHash（可选） | pending | 当前证据仅为开发者现场验证，尚无独立 Reviewer 签署。 |
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

下一步在隔离环境验证完整栈及配置生命周期，再审查 G0-Base；旧 Diff 的双版本视觉基线独立归 T0-02/G1。
