# 实施状态

当前批次：T0 起步；未改生产设置、未发布、未进入 renderer 产品实现。基线和指纹见 [compatibility.md](compatibility.md)。

| ID | 状态 | 证据与缺口 |
|---|---|---|
| T0-01 | running | 已记录本机 CLI/SDK 指纹、安装版本和包导出键；待核对公开源码树、实际解析指纹与全部根导出。 |
| T0-02 | running | 已登记旧入口、源码指纹、配置分支及锁与实际依赖漂移；待冻结匿名旧视觉 fixture、HTML 及许可归属。 |
| T0-03 | running | `python3 tests/pty/smoke.py` 在隔离 HOME、Agent dir、临时 cwd 和空白 session 中成功执行真实 Pi 1.6.0；本地 SDK faux provider 发起一次 `read`，屏幕出现 `PROBE_DONE`，无真实认证或付费模型。 |
| T0-04 | running | 同一工具行实际显示两个 slot；call 与 result 共享 state，各 slot 获得其已返回实例；两者收到 `outputPad=1`。Ctrl+O 将 final 的 `expanded=false` 切至 `true`；两次正文相同、无错误。待验证排序、自定义下游、历史/reload、主题、无 UI、异常回退。 |
| T0-05 | running | 实测 Ai 和 TUI 包根可由宿主加载；Ai `/providers/faux` 子路径在本次加载器中不可解析。尚未验证产物入口、peer 与高亮行为。 |
| T0-I、T0-B1…B3、T0-W1…W2、T0-R1…R2、T0-RH | pending | 公共 Read 探针不替代各工具的专用探针。 |
| G0-Base、G0-Bash、G0-Write、G0-Read、G0-ReadHash（可选） | pending | 当前证据仅为开发者现场验证，尚无独立 Reviewer 签署。 |
| G1-Migration、G2-Shared（Bash/Write/Read）、G3-Bash、G4-Write、G5-Read、G5-ReadHash（可选）、G6、G7 | pending | 未到进入条件。 |

下一步补 resolver 顺序、历史与无 UI 的真实宿主证据，并用隔离环境分别采集旧 Diff 锁定版与实际安装版的视觉基线，再审查 G0-Base。
