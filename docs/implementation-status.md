# 实施状态

当前批次：1.0.0 已发布到 `latest`；未改生产设置、未切换生产。基线与指纹见 [compatibility.md](compatibility.md)，门禁见文末。

| ID | 状态 | 证据与缺口 |
|---|---|---|
| T0-01 | passed | 已记录本机 CLI/SDK 指纹、安装版本、包导出键与根导出差异；固定 commit 的 `ToolRenderContext` 文本与安装声明逐项一致。构建产物整体对应关系未证，已记入 compatibility。 |
| T0-02 | passed | 旧源码、配置分支与指纹已冻结；真实 PTY 冻结原生 Edit 与 Hashline 的 0.4.2/0.5.1 卡片 golden，见 `tests/fixtures/migration/`。 |
| T0-03 | passed | `python3 tests/pty/smoke.py` 在隔离 HOME、Agent dir、临时 cwd 和空白 session 中成功执行真实 Pi 1.6.0；本地 SDK faux provider 发起一次 `read`，屏幕出现 `PROBE_DONE`，无真实认证或付费模型。 |
| T0-04 | passed | 已实测行级 state、slot 组件复用、`outputPad=1`、展开、无 UI、resolver 顺序、下游回退、历史回放、`/reload`、结果构造异常回退及进程内主题切换。`smoke.py` 现在断言 call 首次不复用、后续复用、两个 slot 均 `outputPad=1`、result 共享 state 且展开前后各渲染一次。 |
| T0-05 | passed | 已验证公开高亮、宽度、ESM 打包入口和 Pi 受管安装的 peer 处理；宿主 SDK/TUI 与 `pi-ui@0.4.2` 可用。实际候选包安装归 T1/T7。 |
| T0-I | passed | 隔离核心栈与完整用户扩展栈均启动成功；完整栈的 TUI 读取已进入 renderer。真实审批与 Compressor 改写不属本任务。 |
| T0-RH | passed | 范围改写、错误跳过、截断与 details 共存、图片保留、历史回放均已实测；0.1.2 无锚点隐藏能力，标 unsupported。 |
| T0-B1 | passed | 成功/空/非零/流式/空首帧/Gate allow/拒绝/超时/执行超时/计数/模型第二轮结果均采集；`ctx.abort()` 真实 AbortSignal 覆盖审批中与执行中取消（计数 0）；新会话与去掉 durationMs 的旧格式会话均回放验证。 |
| T0-B2 | passed | 行截断、1500 行/63000B 字节截断、60KB 单行、截断+执行超时；真实 AbortSignal 在 3000 行输出后取消，计数 0。 |
| T0-B3 | passed | 非幂等计数：批准前 0、allow 恰 1；Esc/approval 超时/执行超时/AbortSignal 均 0；Gate+Compressor 栈 A/B 真实触发压缩，模型结果逐字一致，originalChars=1000→153。 |
| Bash slot | passed | A 否决、B 无 result 结构不足；候选 C 通过成功/错误/截断：原生 shell 与 outputPad=1，命令一次，诊断文本进入 result。 |
| T0-W1 | passed（部分矩阵） | final/args/bytes 与 9–10 次 argsComplete=false 快照成立；替换/缩短/path 变化/abort 未单列。 |
| T0-W2 | passed（单场景 A/B） | 成功场景 OFF/ON bytes/args/result/次数一致；失败/取消/历史文件修改未做 OFF/ON。 |
| T0-R1 | passed | 基础/范围/EOF/limit=0/空文件/同形 notice/行截断/字节截断/超长首行/Markdown/非法 offset/历史回放均采集；非法 fractional limit 未单列。 |
| T0-R2 | passed | 图片/unsupported/processImage 失败/mixed 与 showImages 上下文均已采集。 |
| G0-Bash | passed | G0BashReview 第五轮签署（correct，0.99）：Pi 1.6.0、顶层 Bash、Gate 0.1.6、已验 Compressor、slot C。 |
| G0-Write | signed | T0-W1/W2 + G4 复审签（correct，0.90）。 |
| G0-Read | signed | 第三轮复审 sign（correct，0.93）：伪行号已消除，T0-R1/R2 证据有效。 |
| G0-ReadHash（可选） | pending | 未启动。 |
| G1-Migration | passed | Migration profile 已由 G1MigrationReview 签署（correct，0.99），范围仅 Edit/Hashline。 |
| G2/G3/G4/G5/G6 | signed | Bash/Read/Write、安全栈、混合版本、集成矩阵已签。 |
| G7 | signed | G7FinalReview sign：1.0.0，`latest=1.0.0`。 |

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

图片读取保留原生 `text` + `image` 两块，文本为 `Read image file [image/png]`，Hashline 未写入锚点。历史回放复用同一 `--session` 时，renderer 收到与首次完全相同的改写正文，没有重新执行 Read。0.1.2 未提供 `hideHashAnchors` 行为，隐藏能力标 unsupported。

## G0-Base 门禁记录

| 字段 | 内容 |
|---|---|
| 状态 | passed（G0BaseReview 复审：correct，confidence 1.0） |
| owner | Main |
| baseline SHA | `d02227b01fea8d9770b1dd8d5d22043b258902d8` |
| implementation SHA | `72ebc8b2312753cda73b5fdd87e2931b8305339a` |
| 命令/环境 | `python3 tests/pty/smoke.py`、`package-smoke.py`、`managed-install-smoke.py`、`full-stack-smoke.py`、`uv run --with pyte python tests/pty/migration-baseline.py`；Pi 1.6.0，隔离 HOME/Agent dir/cwd |
| 实际结果 | 脚本全部退出 0；T0-01 新增固定 commit tree 与源码 SHA；T0-04 新增 `outputPad`、call slot 复用断言 |
| 限制 | 构建产物无法逐字节复现；未验证真实审批/Compressor；T0-RH 隐藏锚点能力在 Hashline 0.1.2 标 unsupported |
| 独立 Reviewer | G0BaseReview 首轮 blocked（T0-01 缺 checkout、T0-04 缺字段断言）；复审 T0-01 passed，T0-04 仍 blocked：`all(calls[1:])` 在仅一次 call 时为空真。已加 `len(calls) >= 2`，`smoke.py` 重跑退出 0（16 次 call 事件）。 |
| follow-up | 复审通过，无剩余阻断；后续 SDK/slot/配置契约变化需重新打开 |
| G0-Base | passed（reviewer G0BaseReview，2026-11-26） |

## T1 迁移进展

打包矩阵证据见 `docs/evidence/tarball-matrix.json`；`uv run --with pyte python tests/pty/tarball-matrix.py` 会重新生成。

| ID | 状态 | 证据与缺口 |
|---|---|---|
| T1-01 | passed | 干净 clone 经 `npm ci` + `npm pack` 产出 dist 入口；tarball 隔离安装、`npm ls` 无 Pi runtime；`npm test` 22、typecheck、oxlint 通过。 |
| T1-02 | passed | 卡片等于 golden；真实 TUI `/export` 预渲染 call/Diff 旧新一致且含正文；tarball 矩阵确认文件字节与工具结果文本一致。`behavior-matrix.py` 覆盖 light 主题、Ctrl+O 展开与 edit 错误回退；`hashline-cases-matrix.py` 覆盖 noop 与多文件；`tarball-matrix.py` 含 Hashline ON 的 tarball 等价；`full-stack-ab.py` 覆盖完整栈 A/B；`downstream.py` 验证 OFF 返回 PEER_EDIT、后加载自定义 renderer 在 ON 时仍优先；`diff-factory.test.ts` 覆盖 adapter 抛错回退；`command.test.ts` 覆盖 force 写入/备份与取消。 |
| T1-03 | passed | schema、显式迁移上下文、`/tool-ui-migrate` 预览/备份/原子写入与入口诊断已实现并有单测；PTY 已验证 dry 不落盘、取消不写入；force 写入由单测覆盖，确认对话框 PTY 未打通。 |
| T1-04 | passed | `src/integration/resolver.ts` 每次调用 `next()` 一次；Edit 只换 `renderResult`，Hashline 换 shell 与 result，call 保留；关闭/未知/无下游返回原对象。 |
| T1-05 | passed | `migration-parity.py`、`tarball-matrix.py`、`full-stack-ab.py` 覆盖旧配置、关闭、native-only、真实 tarball、双加载拒绝与完整栈 A/B。后加载下游优先；未做 adapter 抛错的 peer 回退专项。 |
| T1-06 | passed | 用户批准后已发布 `0.1.0`；`pi install` 干净安装、golden 卡片、无 Pi runtime 均通过。npm 自动写入 `latest` 且 token 无权限移除，偏差见 release-evidence。 |
| G1-Migration | passed | G1MigrationReview 最终签署（correct，0.99）；`latest` 偏差接受为非阻断限制。 |

## T2 / Bash 进展

| ID | 状态 | 证据 |
|---|---|---|
| T2-02 | passed | `ToolCard` 单测 + snapshot；分区行保留白名单 SGR，宽度/空分区/控制字符覆盖。 |
| T2-03 | passed | `CodeBlock` 单测 + snapshot；head/tail、折行、offset、视觉截断提示、1 MiB/20k 行与超大单行上限。 |
| T2-04 | passed | `OutputBlock` + 安全 SGR；剥离 OSC/CSI/控制符/扩展 bidi；超大单行/20k 行上限、显式空行保留。 |
| T2-06 | passed（Bash） | pi-ui `BashView` + gallery fixture；146 单测通过。 |
| T2-07 | passed | pi-ui 0.6.x 发布到 next（latest 0.4.2）；README/API、contract 链接、146 单测与 tarball 导出回归完成。 |
| T2-05 | pending（Bash/Write/Read 不消费） | `command.highlight` 在 slot C 下 unsupported；产品命令由原生 call 独占，不阻断 Bash profile。 |
| G2-Shared（Bash） | passed | G2G3BashReview 签署：T2-02/03/04/06/07 通过；T2-05 仅 command.highlight unsupported。 |
| T3-01 | passed | `adaptBash`：status/command/output/duration/truncation（含 lastLinePartial/truncatedBy/maxBytes）/fullOutputPath；CRLF 由 View 归一。 |
| T3-02 | passed | 命令 owner 原生 call；截断/路径安全；配置字段；40 列 cwd/长路径保留标题与 basename；PTY 全屏命令一次。 |
| T3-03 | passed | slot C renderer 只替换 result；产品 PTY 命令/标题/正文各一次，成功/截断/错误/展开通过。 |
| T3-04 | passed | 宽度矩阵、narrow 60 列卡片、resize 后 60 列重绘、流式 running 卡片、展开、缓存 key、异常回退与历史均通过。 |
| T3-05 | conditional（已接受） | 执行/args/result/compressor/命令一次/OFF 无卡片实测；cwd 间接证明、schema 静态白名单、请求体未采集、下游 peer 优先级测试，均记录为已接受限制。 |
| G3-Bash | conditional pass | G2G3BashReview 签署，接受 T3-05 限制：cwd 间接证明、schema 静态白名单、provider 请求体未采集、下游 peer 优先级测试。 |

### T1 门禁记录

| 字段 | 内容 |
|---|---|
| 状态 | T1-01…T1-06 与 G1-Migration 全部 passed |
| baseline SHA | `2352122097` |
| implementation SHA | `baf17470e8` |
| 命令/环境 | `npm test`、`npm run typecheck`、`npm run lint`；`uv run --with pyte python tests/pty/{migration-parity,export-parity,tarball-matrix,behavior-matrix}.py`；Pi 1.6.0 隔离 HOME/Agent dir |
| 实际结果 | 28 单测、typecheck、lint 通过；干净 clone 打包含 dist；tarball 安装无 Pi runtime；Edit/Hashline 卡片/字节/结果一致；真实 `/export` 逐字段一致且保留 Diff；light、Ctrl+O 展开、错误回退、noop、多文件、完整栈 A/B、迁移 dry/cancel、force 单测通过 |
| 限制 | migrate force 确认框未打通 PTY（写入/备份由单测覆盖）；`latest=0.1.0` 无法移除（token 403），接受为非阻断；生产切换需用户手动执行 |
| 独立 Reviewer | G1MigrationReview：首轮 blocked；二轮确认 F1/F3 解除；最终签署 G1 passed（correct，0.99） |
| follow-up | 已签署；`latest` 待有权限后调整；生产切换由用户执行 |

### 迁移等价实测

`tests/pty/migration-parity.py` 以本机构建产物作为 settings 的本地 package，隔离 Agent dir，执行与 T0-02 相同的 edit/hashline 场景。开启时两张卡片逐行等于 `tests/fixtures/migration/*-0.5.1.txt`；`toolUi.enabled=false` 时屏幕不再出现 Edit 卡片。旧 `editDiff.nativeEdit=true` 能映射为 Edit+Hashline 启用。

Hashline `/export`：`tests/pty/export-parity.py` 在真实 PTY 中执行 `/export`（会调用扩展 renderer），解析 HTML 内嵌的 base64 sessionData，比较 `renderedTools`。旧扩展与新包的预渲染 call/Diff HTML 一致，正文含 `beta2`。CLI `--export` 不加载扩展 renderer，不能用于此验收。

## T5 Read 进展

| ID | 状态 | 证据 |
|---|---|---|
| T5-01 | passed | `adaptRead`：offset/limit 编号、非正整数 limit/非法 offset 不编号、续读提示不编号、Hashline/图片诊断原文、truncation 边界；11 单测。 |
| T5-02 | passed | `ReadView`：head 12/24、真实行号、truncation 提示、原文回退；产品 PTY 通过。 |
| T5-03 | pending（可选） | 未来 Hashline 锚点隐藏未实现；0.1.2 按原文兼容。 |
| T5-04 | passed | image block 回退原生；processImage 失败纯文本不编号；unsupported 记录 `imageUnsupportedByModel`；showImages OFF/ON 验证。 |
| T5-05 | passed | 原生 OFF/ON 覆盖 basic/range/zero/empty/truncated/process_fail/image；Hashline 0.1.2 range/truncated OFF/ON 锚点保留；content/details 一致、各执行一次。 |
| G0-Read | signed | 第三轮复审 sign：伪行号已消除，T0-R1/R2 证据有效。 |
| G2-Shared（Read） | signed | 第三轮复审 sign：ReadView 契约/单测/文档完成。 |
| G5-Read | signed | 第四轮 delta 复签（correct，0.95）：0.6.9 全无编号预览修复、Hashline 0.1.2 A/B 有效。 |

## T4 Write 进展

| ID | 状态 | 证据 |
|---|---|---|
| T4-01 | passed | `adaptWrite`：path/content/argsComplete/CRLF/lineCount/error notices，5 单测。 |
| T4-02 | passed | head 6、expanded error、尾随 LF、多行诊断、错误隐藏；流式 call 显示路径与 tail，完成/历史 call 仅 `write <path>` 行。证据 `write-call-stream.json`。 |
| T4-03 | signed | 折叠 6/12、展开 200、10k/256KiB；完整 colors revision；append/replace/path 与真实 oracle；复审 sign。 |
| T4-04 | passed | 流式 call 预览；完成/历史 call 仅 `write path` 行；result 独占正文，path/正文各一次。 |
| T4-05 | passed | success/overwrite/error OFF/ON bytes/args/result/次数一致；history 未重跑；参数流式取消不执行/不写文件。 |
| G4-Write | signed | G0/T4-03/04/05 均已签（correct，0.90），附已记录限制。 |

### G2/G3 Bash 签署后 P3 记录

- `clampChars` 未完全对齐 `clampUtf8` 的 emoji/ZWJ、旗帜边界；`clampUtf8` 末尾组合符+ZWJ 顺序可再统一。
- 20k 边界处 `takeLines` + `parts.pop` 可能丢掉真实末尾空行。
- 20 列 `cwd` 行仍可能截掉长 basename 首字符（默认 showCwd=false）。
- `cwdKind='execution'` 由 adapter 无条件设置；history/spawnHook cwd 未单独区分。
- 错误结果尾部折叠尚未单独实现；现有 fixture 诊断在尾部可见。
- resize 后卡片本身仍无直接像素断言，已记录。

## T6 集成进展

| ID | 状态 | 证据 |
|---|---|---|
| T6-01 | passed | 三工具同会话 OFF/ON 一致、卡片互斥、`/reload` 不重跑；产品重复加载仍单卡片；Edit/Hashline 沿用迁移 A/B。 |
| T6-02 | passed | `export-parity` 展开 Diff 正文断言、tools=1；Write/Read 模板导出正文保留；证据已重跑。 |
| T6-03 | signed | 安全复审 sign：Gate+产品卡片 ✓/✗、deny/timeout/exec_timeout 0 次；uv guard 在产品 ON/OFF 均 0 次；Compressor ON/OFF；R2/R3 为 Gate 已知开项。 |
| T6-04 | passed | 产品 0.8.1 + Prompt/TODO（共享 0.5.0）同会话：HUD、band、Write/Read、subagent/goal；Gate 焦点覆盖。 |
| T6-05 | passed | `--print`/RPC Read/Write/Bash 一致；`!`/`!!` 各执行一次无卡片；nested 子会话不加载父 ambient extensions（架构不适用）。 |
| T6-06 | passed | `pack-artifact.py`：干净安装 tarball + pi-ui 0.8.1、无第二套 runtime、无 Hashline 环境 Bash/Write/Read 卡片可用。 |
| G6 | signed | 第三次复审 sign（correct，0.93）；T6-01..06 完成，nested 架构不适用。 |

## T7 发布进展

| ID | 状态 | 证据 |
|---|---|---|
| T7-01 | passed | pi-ui Gallery 渲染 Bash/Write/Read/Edit/TODO/Approval；各 profile 单测/PTY 通过。 |
| T7-02 | passed | packed 启动 +1.9ms、RSS +3.73MiB；视图预算通过；1000 partial/1000 Read/Bash history 压力通过；oracle 171 单测。 |
| T7-03 | passed | pi-ui 0.8.1 + pi-tool-ui 1.0.0 发布到 latest；安装后 README、Edit/Hashline golden、五工具卡片。 |
| T7-04 | passed | Bash/Write/Read 各自 single-off/global/removed 回原生；损坏包失败后三工具恢复；content/files 一致。 |
| T7-05 | signed | 最终 Reviewer sign（correct）：发布、性能、安全、回滚、限制均闭环。 |
| G7 | pending | 依赖 T7-01..05。 |
