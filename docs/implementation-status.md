# 实施状态

当前批次：T0 起步；未改生产设置、未发布、未进入 renderer 产品实现。基线和指纹见 [compatibility.md](compatibility.md)。

| ID | 状态 | 证据与缺口 |
|---|---|---|
| T0-01 | running | 已记录本机 CLI/SDK 指纹、安装版本和包导出键；待核对公开源码树、实际解析指纹与全部根导出。 |
| T0-02 | running | 已登记旧入口、源码指纹、配置分支及锁与实际依赖漂移；待冻结匿名旧视觉 fixture、HTML 及许可归属。 |
| T0-03 | running | `python3 tests/pty/smoke.py` 在隔离 HOME、Agent dir、临时 cwd 和空白 session 中成功执行真实 Pi 1.6.0；本地 SDK faux provider 发起一次 `read`，屏幕出现 `PROBE_DONE`，无真实认证或付费模型。 |
| T0-04 | running | 真机已验证共享 state、各 slot 组件复用、`outputPad=1`、Ctrl+O 展开、无 UI、resolver 顺序、自定义下游保留和历史回放。待验证 reload、主题、异常回退。 |
| T0-05 | running | 实测 Ai 和 TUI 包根可由宿主加载；Ai `/providers/faux` 子路径在本次加载器中不可解析。尚未验证产物入口、peer 与高亮行为。 |
| T0-I、T0-B1…B3、T0-W1…W2、T0-R1…R2、T0-RH | pending | 公共 Read 探针不替代各工具的专用探针。 |
| G0-Base、G0-Bash、G0-Write、G0-Read、G0-ReadHash（可选） | pending | 当前证据仅为开发者现场验证，尚无独立 Reviewer 签署。 |
| G1-Migration、G2-Shared（Bash/Write/Read）、G3-Bash、G4-Write、G5-Read、G5-ReadHash（可选）、G6、G7 | pending | 未到进入条件。 |

### Resolver 顺序实测

`python3 tests/pty/smoke.py`：两种显式 `-e` 顺序中，Read 的两个 resolver 均按加载顺序进入，各一次；双方都覆盖结果时，先加载者的结果出现在屏幕。探针排在前面但返回原对象时，屏幕保留后加载的自定义 `PEER_RESULT`。这仅证明显式加载的探针组合，不证明生产栈不存在同名竞争。

历史回放：以 `--print --session` 生成真实会话，修改临时目录中的原文件，再用 PTY 打开同一会话而不提交新提示。renderer 收到保存的旧正文和 final，新进程首次 result 未复用旧组件；无 Read `tool_call` 事件。

下一步补 reload 的真实宿主证据，并用隔离环境分别采集旧 Diff 锁定版与实际安装版的视觉基线，再审查 G0-Base。
