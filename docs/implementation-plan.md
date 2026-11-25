# Pi Tool UI — 完整实施计划 v1.0

> 日期：2026-11-25 · 审阅修订 1。本机静态核对完成，可开始 T0。运行及发布门禁待验。
> 目标包：`@jackice/pi-tool-ui`；共享库：`@jackice/pi-ui`。
> 本文取代 Bash UI v1.1 中由 dotfiles/hashline-diff 承载新 renderer 的决定；保留其已审阅的技术契约。本文是 Tool UI 的唯一实施规范，不要求另行读取旧 Bash Plan 才能执行。原 pi-ui、pi-prompt、Approval Gate 计划继续约束各自职责。

## 0. 冻结决策与实施原则

| ID | 决策 | 不允许的替代 |
|---|---|---|
| D01 | 新建独立发布的 pi-tool-ui；先迁移现有 Edit/Hashline，再增量交付 Bash/Write/Read | 在旧扩展继续叠加功能；从零重写稳定 Diff |
| D02 | 原生 Pi SDK `registerToolRenderer` 是唯一工具接入机制 | registerTool、包装 execute、修改工具 schema、替换执行器 |
| D03 | pi-ui 提供纯 View/布局；pi-tool-ui 提供配置、结果适配和宿主绑定 | pi-ui 反向依赖业务、全局 Agent Runtime |
| D04 | Hashline 是可选兼容目标，不是安装依赖 | import Hashline 执行器、要求安装 Hashline 才能启动 |
| D05 | OMP、Powerline、hashline-diff 不进入生产或构建依赖树 | fork、monkey patch、私有成员、运行时加载参考项目 |
| D06 | 每个工具独立开关、独立探针、独立回退；默认新安装全部关闭 | 一项失败导致其他已验收工具不能发布 |
| D07 | 只消费宿主最终提供给 renderer 的内容；不以 UI 为理由修改模型数据 | 从磁盘重读、恢复被截断内容、替换 compressor 输出 |
| D08 | 迁移阶段保持旧视觉和配置行为；共享化属于后续可选增量 | 同时更换包、重写 Diff、改视觉和执行语义 |
| D09 | 新卡片仅用于顶层模型发起的 TUI tool rows，迁移保留旧 Hashline HTML 导出 | 接管 `!`/`!!`、codemode 嵌套工具、Python 执行、Editor/Footer |
| D10 | TDD + 每项 Coding 任务独立 Reviewer；证据不足的门禁保持 pending/blocked | 以截图、静态检查或 reviewer 未执行代替真实运行证据 |

**发布分两级**：Migration release 仅 Edit/Hashline；Full release 增加通过各自门禁的 Bash/Write/Read。完整 v1.0 产品目标必须五工具均通过；若某切片阻断，可标记为部分能力发布，但不得宣布完整目标完成。默认所有开关关闭指全新安装，迁移配置则恢复旧实际启用值。

## 1. 范围与视觉规格

### 1.1 支持矩阵

| 工具名 | 数据 | 目标 | 首版限制 |
|---|---|---|---|
| edit | 现有 native edit adapter | 原样迁移 Diff | 不修改现有 CodeFrame 契约 |
| hashline | 现有 Hashline adapter | 原样迁移 Diff | 旧版摘要按旧语义展示，不伪造精确 diff |
| bash | args.command + host result | 命令、状态、Output、尾部预览 | 不推断退出码，不读取输出文件 |
| write | args.content + host final | 代码、行号、流式尾部/完成头部 | 内容是调用参数预览，不证明磁盘最终字节 |
| read | host result + args + 已证明的协议 | 代码、行号、范围、截断 | Hashline 0.1.2 保留锚点原文；来源或正文边界不明时无行号；图片宿主管理 |

非目标：工具执行、权限策略、Session 持久化、文件读取/写入、LSP、Shell Trace、终端模拟器、Markdown/图片引擎、URL Scheme、全局快捷键、编辑器与 Footer。Read Markdown 首版显示源码，不引入 Markdown 渲染模式。工具卡片与消息级 Token/Cache/tps 展示独立。

### 1.2 视觉 fixture（非实测）

```text
╭─ Write: test.html · 12 lines ───────────────────╮
│   1 <!doctype html>                            │
│   2 <html lang="zh-CN">                         │
│   … 10 more lines                              │
╰────────────────────────────────────────────────╯
╭─ Read: src/main.ts · 21–32 ─────────────────────╮
│  21 export function main() {                   │
│  22   return run();                             │
│   …                                            │
╰────────────────────────────────────────────────╯
╭─ Bash ✓ · 2.8s ────────────────────────────────╮
│ $ pnpm test                                    │
├─ Output ────────────────────────────────────────┤
│ … earlier display rows hidden                  │
│ Tests 128 passed                               │
╰────────────────────────────────────────────────╯
```

以上宽度和数据仅展示结构；实际行数按下表和纯布局测试确定。优先单圆角卡片；若宿主探针证明不可行，允许两个 slot 组成同一逻辑卡片或原生外框内定制内容（见 §5）。不得因视觉要求破坏工具行为。

| 区域 | 折叠逻辑行 | 折叠视觉行 | 方向 |
|---|---:|---:|---|
| Write 流式参数 | 12 | 18 | tail |
| Write 参数完成至 final | 6 | 18 | head |
| Read 可确认正文 | 12 | 24 | head |
| Bash 命令 | 无另设 | 6 | head |
| Bash 输出 | 无另设 | 12 | tail |

视觉预算仅指正文行，不包括 header/border/隐藏摘要/必要诊断。逻辑行先选，再按 ANSI/字素宽度换行并限制视觉行；tail 保留末尾视觉行；head 保留开头视觉行。隐藏摘要分别说明逻辑行和视觉行，不将被裁切的一部分长行称为完整隐藏逻辑行。Expanded 展示宿主提供的可用数据（不恢复 native truncation）；极端内容允许显示明确安全资源上限提示，默认上限见 §7.4，不得静默截断。空正文不制造空白区域。失败诊断优先于折叠预算。

## 2. 证据与版本基线

### 2.1 来源等级

- L：2026-11-25 核对的本机安装产物、有效配置与 dotfiles 源码。
- S：公开源码参考。固定引用的可访问性及与本机 dist 的对应关系由 T0 登记。
- H：设计假设，须运行探针关闭。不得以 S 或 L 代替 PTY。

| 项目 | L 基线（实施时重新采集） |
|---|---|
| Pi / Node / OS | Pi 1.6.0 Bun 全局安装，Node 25.9.0，macOS 26.7.3 arm64 |
| hashline-diff | dotfiles 本地扩展，锁定 pi-ui 0.4.2，editDiff.nativeEdit=true |
| Hashline | @jackice/hashline 0.1.2 |
| Approval | @jackice/pi-approval-gate 0.1.6，嵌套 pi-ui 0.4.2，guard=uv |
| TODO | @jackice/pi-session-todo 0.1.2，嵌套 pi-ui 0.4.2 |
| Prompt | @jackice/pi-prompt 0.2.1，解析到 pi-ui 0.5.0，`footerMode: "none"` |
| Shell Compressor | 本地扩展，启用；成功 Bash 的 final 可能被改写 |
| Theme | catppuccin-mocha |

pi-ui 0.5.0 已安装（L）。T0 分别记录实际 exports、registry 版本、安装解析路径和产物指纹。当前公共 CodeFrame 消费 diff hunks，公共 API 尚无 ToolCard。Powerline 不在活动包列表（L），正式验收另做零依赖环境。

### 2.2 固定公开参考

原计划引用 Pi v1.6.0 commit `faac585884ae2c013a6b1400f3e9e77f10b34bac`。与本机安装包的对应关系尚未核实。

- [SDK types](https://github.com/earendil-works/pi/blob/faac585884ae2c013a6b1400f3e9e77f10b34bac/packages/coding-agent/src/core/extensions/types.ts#L488-L520)：args/toolCallId/state/lastComponent/cwd/argsComplete/executionStarted/isPartial/isError/expanded/showImages/durationMs/outputPad；types 的字段含义不证明审批或最终执行文本。
- [Read tool](https://github.com/earendil-works/pi/blob/faac585884ae2c013a6b1400f3e9e77f10b34bac/packages/coding-agent/src/core/tools/read.ts#L297-L355)：offset 真值分支、limit、firstLineExceedsLimit、truncation.content、continuation 文本；limit 提前结束可能无 details。
- [Read renderer](https://github.com/earendil-works/pi/blob/faac585884ae2c013a6b1400f3e9e77f10b34bac/packages/coding-agent/src/core/tools/renderers/read.ts#L111-L185)：原生折叠隐藏正文、图片不支持警告、details 截断提示。
- [Write tool](https://github.com/earendil-works/pi/blob/faac585884ae2c013a6b1400f3e9e77f10b34bac/packages/coding-agent/src/core/tools/write.ts)：path/content、写成功文本。
- [Write renderer](https://github.com/earendil-works/pi/blob/faac585884ae2c013a6b1400f3e9e77f10b34bac/packages/coding-agent/src/core/tools/renderers/write.ts)：WriteHighlightCache、argsComplete、原生成功 result 无正文。
- [Bash tool](https://github.com/earendil-works/pi/blob/faac585884ae2c013a6b1400f3e9e77f10b34bac/packages/coding-agent/src/core/tools/bash.ts)：partial、truncation、fullOutputPath、structuredContent（TUI 可见性另验）。

OMP Read/Write 参考 commit `8d1c55d4082b714e1967871db5e2be04ac327d19`：

- [Write painter](https://github.com/can1357/oh-my-pi/blob/8d1c55d4082b714e1967871db5e2be04ac327d19/packages/coding-agent/src/ui/styles/tools/write.ts)：STREAM_ROWS=12、PREVIEW_ROWS=6、GUTTER_MIN=3、tail 高亮从文件头保持词法状态。
- [Read painter](https://github.com/can1357/oh-my-pi/blob/8d1c55d4082b714e1967871db5e2be04ac327d19/packages/coding-agent/src/ui/styles/tools/read.ts)、[Read presenter](https://github.com/can1357/oh-my-pi/blob/8d1c55d4082b714e1967871db5e2be04ac327d19/packages/coding-agent/src/ui/tools/read.tsx)：读取范围、代码/Markdown/图片、诊断；不移植 URL/资源机制。
- Bash 参考 [painter](https://github.com/can1357/oh-my-pi/blob/76b7d843d59bc83cc40cd5decadc89dc808a14e6/packages/coding-agent/src/ui/styles/tools/bash.ts) 与 [presenter](https://github.com/can1357/oh-my-pi/blob/76b7d843d59bc83cc40cd5decadc89dc808a14e6/packages/coding-agent/src/ui/tools/bash.tsx)，commit `76b7d843d59bc83cc40cd5decadc89dc808a14e6`；此前已读主分支对应文件，固定版本是否与该文件逐字对应由 T0 复核。OMP 仅为视觉/组织参考，不能作为 Pi SDK 实现依据。

T0 用隔离 checkout 记录 commit/tree/文件 SHA，若参考不可获取，记录原因并仅使用可复核材料；参考不可获取不阻断原生 UI。禁止从参考仓库运行时导入代码。迁移自己的旧实现须核实许可证、作者及归属；如确实复制外部源码须遵守许可并保留 NOTICE，否则独立实现。

## 3. 架构、仓库、发布契约

```text
Native Pi execution (including Gate/Hashline/compressor hooks)
  -> host args/result + public ToolRenderContext
  -> pi-tool-ui adapter (per-row state, no execution)
  -> immutable view model
  -> pi-ui pure View + components
  -> native Component.render(width)
```

```text
pi-tool-ui/
  src/index.ts                 # Pi extension entry; one resolver
  src/config.ts                # validation + pure legacy mapping
  src/integration/resolver.ts  # selection, slot binding, fallback
  src/integration/row.ts       # state/slot protocol (only if proven shared)
  src/adapters/{edit,hashline,bash,read,write}.ts
  src/renderers/{edit,hashline,bash,read,write}.ts
  tests/{unit,fixtures,integration,pty,benchmarks}/
  docs/{implementation-plan,compatibility,implementation-status,migration,release-evidence}.md
  package.json / lockfile / tsconfig.json / README.md / CHANGELOG.md
pi-ui/
  src/components/{tool-card,code-block,output-block}.ts  # use existing Panel etc.
  src/views/{edit,bash,read,write}/
  src/render/{preview,path-label}.ts                     # pure helpers if needed
  tests/ / examples/ / docs/
```

这是逻辑目录，不要求无必要拆文件。旧 Edit/Hashline adapter 先原样迁移；其 View/CodeFrame 继续由现有 pi-ui exports 提供。纯 View 不 import Pi coding-agent，语法高亮由扩展注入已验证公开函数。可依赖 Pi TUI 公共类型/函数（遵循现有包约定），不得引入第二套 Pi runtime。所有 render 同步、无文件 I/O、网络、子进程、定时器或业务事件订阅。配置读取和诊断在接入层负责；渲染异常的诊断按类别限频，不包含源代码/命令/路径。无全局 toolCallId Map、动态注册中心或通用 Provider 框架。

### 3.1 包与版本

- pi-tool-ui 独立 npm 包，采用 ESM，TypeScript，使用实际 Pi 扩展加载器验收的 entry（建议 `dist/index.js`，若 loader 不支持则冻结验证过的 TS entry）。`package.json` 的 `pi.extensions` 指向真实打包入口；不得在发布包依赖源码工作区。
- `@jackice/pi-ui` 是声明的 runtime dependency，固定到验收版本（精确版本，锁文件；禁止隐式 latest）。迁移 release 优先使用旧扩展实际解析的 0.4.2，若必须使用 0.5.0，先通过旧/新库的单独 A/B；Full release 使用含新 Views 的实际发布版。
- Pi SDK/TUI runtime 依赖优先 peer（首版支持 Pi 1.6.0，精确 peer 或经验证的同版本范围，不承诺未测版本）；构建开发依赖锁定，验证真实 loader 解析。若 peer 安装模式不提供运行时包，须用 Pi 公开宿主解析机制实测，不在发布包复制 Pi runtime 作为补救。
- 新 pi-ui 版本建议 0.6.0（仅计划号；T2 检查 registry 和源码分支再冻结），preserve `.`, `./diff`, `./views/edit`, `./views/todo`, `./views/approval` 及 0.5.0 实际新增 exports；新增 ToolCard/CodeBlock/OutputBlock 及 View 入口通过根或明确子路径，选择与现有 exports 风格一致，记录 export map。不得破坏 0.4.2/0.5.0 消费者的已声明契约。
- 不强制 Approval/TODO/Prompt 同时升级其嵌套 pi-ui；测试实际混合版本组合。新组件依赖窗口以发布版本和公开 API 测试为准。
- package tarball `npm pack --dry-run`/实际 pack、干净安装、`npm ls --all`、lockfile、实际 resolver 路径及 Pi 启动共同验收；开发测试可锁定 SDK，生产依赖树不能包含 OMP/Powerline/hashline-diff/Hashline。Hashline 只作为隔离集成测试中的独立安装目标，不作为必需 devDependency。旧源码和旧扩展缺席时完整构建及核心测试必须通过。

### 3.2 文档落地

本文需提交 `pi-tool-ui/docs/implementation-plan.md`。pi-ui 仓 `docs/pi-ui-implementation-plan.md` 增加本计划 T2 组件、版本及兼容门禁的增量章节（或单独受版本控制的 `docs/tool-ui-contract.md` 并从主文档链接），明确旧 Bash v1.1 的扩展宿主已被取代。pi-prompt 不修改。记录两个实际 commit、文件 SHA、接口/exports 对账和 Reviewer；未提交前不得称已同步。T2 发布前完成该动作，不阻断 T0/T1。

## 4. 配置、所有权与迁移

### 4.1 唯一生产配置

Pi settings.json 的 `toolUi`（T0 核实 `pi.getSettings()`、设置层级、首次 render 与 reload 时序）。所有字段缺省值如下：

```json
{
  "toolUi": {
    "enabled": false,
    "tools": {
      "edit": { "enabled": false },
      "hashline": { "enabled": false },
      "bash": { "enabled": false, "command": { "highlight": true, "previewRows": 6 }, "output": { "previewRows": 12, "ansi": true, "showTruncation": true, "showFullOutputPath": true }, "showDuration": true, "showCwd": false },
      "write": { "enabled": false, "highlight": true, "lineNumbers": true, "previewLines": 6, "streamingPreviewLines": 12, "maxPreviewRows": 18 },
      "read": { "enabled": false, "highlight": true, "lineNumbers": true, "previewLines": 12, "maxPreviewRows": 24, "hideHashAnchors": false }
    }
  }
}
```

当前旧扩展的 Edit 仅在 `editDiff.nativeEdit === true` 时启用，本机为 true。Hashline 默认启用，仅在 `PI_HASHLINE_DIFF` 的值恰为字符串 `0` 时关闭。T1 清点实际设置与加载入口；迁移报告记录 schema v1、源值和目标值，未识别旧设置须报告并保留于备份。

校验：object/boolean 严格类型；preview 数值必须有限整数 1..100；未知 key 报一次诊断并拒绝对应工具配置，顶层无效则全关闭。缺省字段用冻结默认值，不作字符串隐式转换。生效为启动/已验收 reload 边界；不支持运行态热切换。ANSI 安全过滤始终开启；showTruncation/showFullOutputPath 只控制附加结构化提示，不能隐藏宿主唯一诊断。开关仅影响 UI，不写 settings、不修改工具列表。用户手动/显式迁移应用配置。

### 4.2 Resolver 所有权

每进程一次注册；每次调用 `next()` 恰好一次；未知名、关闭、未验收能力、下游无可用契约全部返回原对象（包括 undefined）。启用且获得明确配置所有权时，仅覆盖该工具已验证的 renderer 字段。迁移 Edit 保留原 `renderShell` 与 `renderCall`，只替换 `renderResult`；迁移 Hashline 保留原 `renderCall`、原有 `self` 外框与结果回退。Bash/Write/Read 按各自冻结的 slot 方案选择字段。不得根据 `next()` 返回对象猜测下游来源。只使用精确名称 edit/hashline/bash/read/write；同名替代工具若不能证明结果契约匹配，则安全文本展示或不启用。配置前检查活动扩展和加载顺序；冲突时拒绝启用对应工具。以隔离环境及显式用户配置确认所有权。

```ts
// 示意：真实类型从 Pi 公共 SDK 导入；不存在 original 时保持原样。
pi.registerToolRenderer((name, next) => {
  const original = next();
  const factory = getEnabledVerifiedRenderer(name, config);
  if (!original || !factory) return original;
  return factory(original); // only renderer fields
});
```

T0 测试原生下游与自定义下游、前后加载顺序、resolver 调用次数。旧 hashline-diff 与新包禁止在同一生产进程同时加载（即使部分工具关闭），迁移对照分别隔离运行。其他 renderer 可并存，但不得竞争已选工具；不尝试覆盖前置 resolver。无 UI 环境不改变 schema/执行/权限，不要求显示卡片。

### 4.3 T1 一次性迁移事务

1. 清点旧扩展路径 `dotfiles/pi/.pi/agent/extensions/hashline-diff/`、源码、入口、实际 settings、锁文件、pi-ui 解析路径、配置分支、exports、测试与现有输出。冻结旧 commit/文件 SHA 和匿名化 fixture；本机不可见，不能跳过。
2. 建新仓和包；复制自己现有 adapter/renderer 实现与相关测试，保留行为；仅改 import、入口、配置桥及包名。迁移期间禁做 Diff 结构重写；禁止把 Hashline 工具代码复制进来。
3. 生成 dry-run 映射报告。按 §4.1 计算旧开关的有效值，分别映射为 `toolUi.tools.edit.enabled` 与 `toolUi.tools.hashline.enabled`。无已有新配置时将 `toolUi.enabled` 设为两者的逻辑或。覆盖 `PI_HASHLINE_DIFF` 未设置、为 `0` 及为其他值的情形，迁移采用当时的有效值。已有新配置优先并报告冲突。未交付的 Bash/Write/Read 保持关闭，已有 `bashUi` 记录后续映射。备份旧文件，经用户确认后以同目录临时文件和 rename 应用设置，失败恢复原文件。扩展启动只读配置。
4. A=旧扩展原锁定版本，B=新扩展迁移版；各用独立 PI_CODING_AGENT_DIR、Session/临时工作目录、确定性 provider，比较 Diff fixture/可见行/展开/主题、Hashline `/export` 的 call 与结果正文、模型请求/result、文件字节、工具执行次数、耗时和 RSS。新增组件不得出现在这次对照的变量中。记录允许的 ANSI/动态时间差异，不能用大范围归一化掩盖退化。
5. G1 通过后先在隔离真实包验证，备份生产 settings 与旧目录/lock；退出 Pi；移除旧扩展的所有发现入口（不仅 npm 包列表，本地扩展目录也须移出发现范围），安装新包并应用迁移配置，重启。验证只有一个 resolver owner，Read/Write/Bash 仍关闭。旧备份置于不会被 Pi 扫描的位置。若失败执行下述回滚。
6. 回滚一级：关闭故障 tool 或全局开关，重启恢复完整下游 renderer。二级：新包无法加载时退出 Pi，移除其所有加载入口、恢复旧配置和旧扩展/lock、按原锁重装、重启。无旧扩展的新用户只恢复原生 Pi，不要求安装旧包。迁移成功后旧扩展不再作为运行时或回退前置依赖。

G1-Migration 不依赖新增 ToolCard/Read/Write/Bash；若旧实现无法迁移等价，暂留旧扩展，禁止生产双加载。新工具可以在隔离环境继续开发，但不能在生产接管旧 Diff 直到 G1 通过。

## 5. 公共 Renderer 宿主契约（T0 必证）

L 静态证据：加载顺序 resolver；call 后 result；同一工具行共享 context.state，两个 slot 各有 lastComponent；self 接受完整宽度并自己应用 outputPad；当前 TUI result 仅 content/details，`structuredContent` 不可假定可见。必须逐工具确认实际 installed SDK/dist 与公开 tag 的差异。

### 5.1 Slot 方案与回退

| 顺序 | 候选 | 验收 |
|---|---|---|
| A | call slot 唯一卡片；result slot 更新 shared row state，返回独立零行 Component | 同轮最新状态、无递归 invalidate、无重复边框/内容、点击及展开正常、图片宿主正常 |
| B | 两 slot 组成一张逻辑卡片，各自只渲染负责部分 | 状态一致、外框不重复、结果不出现时结构完整 |
| C | 保留原生 shell，定制内部 | 不再扣宿主 padding、不重复标题/内容、诊断完整 |
| D | 不接管该工具 | A/B/C 均失败则该切片 blocked |

Bash、Write、Read 通过各自 T0 探针冻结方案，Read 图片单独验证。T1 迁移继续沿用旧 Edit/Hashline slot。Pi 1.6.0 通过同一 resolver 渲染 Hashline HTML，内置模板处理 Bash/Read/Write/Edit。导出先将 call 转成 HTML，再单独渲染 result，候选 A 的零行 result 无法补上已生成的 call HTML。因此 Hashline 保留独立 result slot，并用 §4.3 的导出对照验收。SDK 没有公开的渲染界面标记，不通过宽度或 context 字段猜测导出。Pi 升级时复核模板分流。运行中失败在所选外框内使用安全紧凑文本，无法安全展示时用固定诊断。关闭配置后重启或经验证的 reload 可恢复下游完整外框。

### 5.2 行级生命周期

建议 per-row state：独立命名空间、工具名/调用 ID、call snapshot、result snapshot、finalSeen、revision、component cache。使用 SDK 实际 `context.state` 对象形态，不能替换宿主对象或污染其他 resolver state。call 更新 args/expanded/theme 等；result 更新当前结果及证据。两 slot 返回不同 Component，不能把同一个实例加入两次。render(width) 只读取当前快照及更新自身有限缓存，不触发宿主 redraw；仅在公开事件确实需要且探针证明时由接入层请求有限刷新。默认零 timer。若共享 state 不稳定则使用候选 C 或 D，不建全局 Map 补救。

finalSeen 只屏蔽同一执行 epoch 的迟到 partial；原生 replay/重新执行如果复用 ID，按宿主新行/新 context 生命周期重建，不能用 ID 跨 Session 判断。连续 final（如 hook 改写或 replay）以宿主最新权威 final 为准，不能因 finalSeen 丢掉更正结果。call 重绘不能将 final 状态重置成 pending。无证明实时处理的历史未完成行 = unknown。每个 slot 的 lastComponent 必须检查类型/归属，不盲目 cast 下游组件。无 dispose 可靠保证时，所有 Component 不持有外部资源，回收依赖宿主释放。

### 5.3 状态表（优先从上向下）

| 条件 | 状态 |
|---|---|
| 已收到 final 且公开 isError=true | error |
| 已收到 final 且公开 isError=false | success（工具成功，不承诺文件字节/exitCode） |
| 当前 Bash 收到可信 partial（含空帧） | running（工具处理进行中，不保证 shell 已启动） |
| Read/Write 有可信执行阶段证据 | running；仅 executionStarted 不足以证明 I/O 开始，显示 pending/处理中而非磁盘写入 |
| Write 实时参数未完成且 content 为 string | streaming |
| 有实时参数生成/调度证据无结果 | pending |
| 其他 | unknown |

`executionStarted` 可早于校验、审批、进程启动。禁止从 `isError=false` 无 result 推断成功。取消/拒绝/超时保留原生文本诊断，除非公开结构化类别已证明，否则统一 error。durationMs 显示“工具调用耗时”，可能含审批，不冒充 shell wall time；历史缺失则省略。cwd 仅在可信实际执行证据时标 execution；否则可标当前 Session CWD，历史不借当前目录伪造旧执行目录。错误正文不可由颜色或字符串关键词推断。

## 6. 数据契约及适配规则

以下均为本项目的只读 ViewModel，而非 Pi 原生类型。适配器使用安装版本公开类型、运行时窄化和 fixture；纯 UI 不解析工具协议。undefined 表示未知或不可用，不伪造 0。传入快照可以共享不可变字符串，不保留所有历史 partial。所有用户可控文本经过 §7 安全处理。

```ts
type ToolStatus = 'pending' | 'streaming' | 'running' | 'success' | 'error' | 'unknown';
interface BaseViewModel {
  readonly toolCallId: string;
  readonly status: ToolStatus;
  readonly expanded: boolean;
  readonly durationMs?: number;
  readonly notices: readonly Notice[];
}
interface Notice {
  readonly kind: 'error' | 'warning' | 'info';
  readonly text: string;
}
interface SourceLine {
  readonly text: string;
  readonly number: number | null; // trusted original line only
}
interface ReadViewModel extends BaseViewModel {
  readonly path?: string;
  readonly requestedOffset?: number;
  readonly requestedLimit?: number;
  readonly source: 'native' | 'hashline' | 'unknown';
  readonly contentKind: 'code' | 'text' | 'markdown-source' | 'image' | 'mixed' | 'unknown';
  readonly lines: readonly SourceLine[];
  readonly language?: string;
  readonly truncation?: ReadTruncation;
  readonly rawFallback?: string;
}
interface ReadTruncation {
  readonly outputLines?: number;
  readonly totalLines?: number; // selected range, not necessarily whole file
  readonly firstLineExceedsLimit?: boolean;
  readonly by?: 'lines' | 'bytes';
  readonly maxLines?: number;
  readonly maxBytes?: number;
}
interface WriteViewModel extends BaseViewModel {
  readonly path?: string;
  readonly content?: string;
  readonly argsComplete: boolean;
  readonly lineCount?: number;
  readonly language?: string;
}
interface BashViewModel extends BaseViewModel {
  readonly command?: string;
  readonly output: string;
  readonly exitCode?: number; // v1.6.0 first release omitted
  readonly cwd?: string;
  readonly cwdKind?: 'execution' | 'session';
  readonly truncation?: {
    readonly totalLines: number;
    readonly outputLines: number;
    readonly totalBytes?: number;
    readonly outputBytes?: number;
    readonly lastLinePartial?: boolean;
  };
  readonly fullOutputPath?: string;
}
```

### 6.1 Bash（完整保留 Bash v1.1 的核心契约）

- `args.command` 是工具调用中可见命令，不宣称等价于 commandPrefix/spawnHook/guard 变换后实际执行文本。当前有效 Bash ToolDefinition 由 Approval Gate 包装原生执行器后注册（L）；新扩展仅接管渲染字段。
- 原生 first partial 是空 content，随后约 100ms 当前输出快照（L）；独立探针采集，替换而非拼接。空首帧表示处理已开始，不表示命令已成功启动。final 采用宿主最终结果，可能经过 Shell Compressor 改写；不得保留原始 partial 替换压缩后的正文。`details.shellCompressor` 仅经真实格式验证后用于说明，缺失则不推断压缩。
- 文本块按原顺序保留，分隔规则固定为相邻块间换行；非文本交由宿主图片能力处理，其他未知类型保留明确说明。不得从结构化执行结果之外解析 stdout 作为可信 exitCode；Pi 1.6.0 TUI 不传 structuredContent（L），首版不显示 exitCode。超时/取消/拒绝保存原始诊断。
- `details.truncation/fullOutputPath` 经类型验证后生成附加说明；宿主文本中原生截断提示仅在与结构化信息及确切尾部边界一致时去重，否则保留。错误结果只有文本诊断时取消尾部折叠，确保诊断可见；受 §7.4 资源上限约束且显式提示。原生 `(no output)` 文本原样保留，空 content 则不预留正文。`fullOutputPath` 只作安全文本，不自动打开/读取，不提供一键执行。
- 首版 scope 顶层 model bash；不接管用户 !/!! 或 codemode 子调用。启用/禁用 A/B 均保留 Gate 与 Shell Compressor，模型侧 final 不变。

### 6.2 Write（参数预览与成功结果严格分离）

1. `args.path`/`args.content` 只接受 string；已证明的旧字段 alias 通过独立 adapter，冲突时不猜测。args 不完整时只显示可信已有部分；invalid content 不 stringify 对象，不调用文件系统。显示 `streaming arguments` 或 `requested content`；无 final 不显示 written。
2. 内容行定义：CRLF 显示归一为 LF；独立 CR 用可见安全转义；空字符串为 0 行；单个末尾 LF 不额外计一个空行（保留其他实际空行）；行数始终来自当前参数快照而非磁盘。保留内容原始 bytes 不改写 args。非 UTF-8/非法代理字符按安全显示替代，不宣称 byte parity。标题 `N lines` 指请求内容，非实际落盘文件行数。
3. 参数未完成且当前实时证据成立：尾部 12 逻辑行、18 视觉行；参数完成切头部 6 逻辑行，不标成功；final success 保留同一请求正文，显示工具成功及宿主成功结果（如果仅冗余标准确认且匹配路径，可折成一条 status，不能丢非标准成功诊断）。final error 显示原生诊断并明确“requested content / not confirmed”；首版错误默认隐藏正文预览，expanded 可看请求内容，绝不称“未写入任何字节”（可能部分写入）。未知 final 的历史行显示 unknown。
4. 不重读磁盘核对内容、mtime、文件存在、权限或生成 Diff。历史回放必须使用当次持久化 args/result，修改/删除文件后仍显示当时的请求。宿主或其他扩展修改 args/content 时只展示可见 args，不冒充最终执行内容。
5. 流式参数快照可能追加、替换、截短、路径改变或被修正；每轮更新以当前 args 为准，不增量拼接。只有严格前缀追加且高亮实现保证词法状态正确时才采用增量高亮；否则重新高亮完整当前内容。跨行注释、模板字符串、HTML 等必须与完整高亮 oracle 对照。高亮过大/失败时纯文本，避免 quadratic；见 §7.4。final/主题/语言变更清理相关缓存。
6. Write 原生成功 result 可能没有专用正文显示，但 result slot 必须更新状态；A/B/C slot 探针分别验证。执行期间是否有 partial 不假定；使用 §5.3 状态证据。

### 6.3 Read（最重要的语义边界）

Read 只消费宿主传入的 result，不再次读文件，不使用当前工作区推断历史路径或内容。先判断错误/媒体，再选择已证明的正文协议。读取范围是请求值，不等于实际行范围。

| 情况 | 处理 |
|---|---|
| final error | 保留诊断，不编号、不按路径高亮错误 |
| 图片或混合 content | 保留原生宿主图片生命周期、showImages、imageUnsupportedByModel 警告；文字 note 不编号；不复制 base64/不重复展示图片 |
| 图片处理失败，仅文本诊断 | Pi 可能返回成功标志和文本说明，同时没有 image block 或 imageUnsupportedByModel。按诊断保留，无源码编号与高亮。正文和诊断无法区分时安全展示原文，省略源码范围及媒体分类。 |
| 原生可信文本+结构化 truncation.content | 仅当确认与宿主正文前缀及协议一致时用该 content 确定正文边界；保留剩余诊断；firstLineExceedsLimit=true 时无源码正文 |
| 原生文本+offset/limit | 正整数 offset（或缺省/0/负整数按已核对 native clamp）可在确认协议与结果范围后编号；limit 不用于凭空生成正文或结束行 |
| 原生 limit 提前结束，无 details | 续读提示可能是正文末尾的相似文本；无独立边界证据时保留完整原始安全文本，不剥离/不编号有歧义区段；宁可整段不编号 |
| Hashline 改写结果 | 仅在已证明来源及版本协议下解析 anchor，保留真实编号和不连续范围；见 §6.4 |
| 未识别格式/多文本 block 边界不明 | 原始安全文本，不标实际文件范围；保留 block 顺序及诊断 |
| 非整数 offset、负/非整数 limit 等 | 不重写宿主选择语义，默认不推断行号；只显示实际请求及可信返回文本 |

**不可辨识性约束**：正常源文件可以包含完全相同的 `[N more lines in file. Use offset=…]`、`[Showing lines …]` 或 Hashline-looking 文本。仅正则/尾行外观不是证明。无结构化 metadata 的 limit 提示和纯文本同形 anchor 在通用 renderer 中无法无损区分；首版必须允许不编号/原样显示的明确降级，不要求所有 Read 都能编号。只有来源及边界能独立证明时才移除附加展示字符。`truncation.totalLines` 可能是选定范围的行数，不标作总文件行数；`outputLines` 与实际行号的关系须 fixture 验证。超长首行说明（可能含可执行 sed 命令）只作文本，不自动执行。`limit=0`、空文件、EOF、错误等保留原生行为，不把空结果误认为成功读取一行。

Read 行号分配规则：真实明确连续正文起点为 1-indexed native start；不连续来源优先显式 number，null 表示非正文/未知；同一逻辑行换行后只首个视觉行显示编号，续行 gutter 留空；裁切中途开始的视觉行不伪造新编号，标示为续行；范围仅根据已确认编号集合生成，非连续显示 `N–M (gaps)` 或只显示 `N lines shown`，不冒充完整区间。无可信编号时整段无 gutter 或显示空 gutter，不从 1 猜测。Markdown 以 source code/text 显示，不执行链接或内嵌控制。

### 6.4 Hashline Read 的兼容范围

已核对本机 Hashline 0.1.2 的 `index.ts`。成功的文本 Read 可能被 `tool_result` hook 改写成 `[PATH#TAG]` 和 `N:TEXT`。图片、失败结果或无法读取文件等路径会跳过改写。hook 只返回 `content`，未提供版本或来源标记。Pi 保留未被替换的 `details`，原生截断元数据可能与改写后的正文并存。

0.1.2 的正式支持范围是安全展示宿主原文，保留锚点、原编号文本和诊断。来源不明时省略新增行号和源码范围。残留的 `details.truncation`、文件名、安装状态和文本形状均无法单独证明来源。原生元数据只有在来源及正文边界均有证据时才用于拆分或编号。

T0-RH 采集改写与跳过改写的真实结果、保留截断元数据的改写结果、同形锚点、历史与媒体。保留原文是 Read 核心验收的一部分。`hideHashAnchors` 缺省 false，当前 0.1.2 即使显式开启也保留原文。未来版本只有在宿主可见来源及版本标记经独立探针验证后，才实现严格全段校验和可选隐藏，并保留显式行号与诊断。旧 Hashline Edit Diff 迁移独立验收。

## 7. 共享组件、宽度与性能契约（T2）

### 7.1 API 最小化

组件使用现有 Panel、Theme、Width、StatusLine。以下为待实现接口，T2 核对现有实际类型，冻结名称/exports 后开发，不能改现有 CodeFrame diff-hunk 签名。

```ts
interface PreviewPolicy {
  readonly direction: 'head' | 'tail';
  readonly maxLogicalLines?: number;
  readonly maxVisualRows: number;
  readonly expanded: boolean;
}
interface CodeBlockInput {
  readonly lines: readonly SourceLine[];
  readonly language?: string;
  readonly showLineNumbers: boolean;
  readonly preview: PreviewPolicy;
}
interface ToolCardInput {
  readonly title: string;
  readonly status: ToolStatus;
  readonly meta?: readonly string[];
  readonly sections: readonly { readonly title?: string; readonly rows: readonly string[] }[];
}
```

实际纯渲染函数应接收 width/theme、高亮注入、预览配置；sections.rows 是本地生成的已安全样式行，不是任意不可信 ANSI passthrough。CodeBlock 负责代码、行号、wrap；CodeFrame 保留 Diff 专用；OutputBlock 负责允许的 SGR、尾部/头部预览和隐藏计数；CommandBlock 首版由 CodeBlock/纯函数组合，不强制单独 export。PathLabel、Preview、SectionDivider 优先纯函数/已有组件，不引入新的框架。ToolCard 负责边框、标题、分区、meta、状态及窄宽；不决定执行状态/路径/协议。主题使用现有 Pi Theme adapter，不写死 catppuccin 颜色。ASCII 无 Nerd Font 依赖；默认仅安全 Unicode 边框/符号，文件图标可选且有 ASCII fallback；以实际 font 能力或用户配置为准，不读取终端私有状态。

### 7.2 宽度算法

全部以 terminal cell width、grapheme cluster 为单位，不用 string.length。`W` 为宿主传入 width；self 模式左右各应用一次 outputPad，`outer = max(0,W-2*pad)`；default 模式已经由宿主扣除，`outer=W`；若 W 无效或 <=0 返回 []。pad 取已验证非负整数并限制可用宽度；T0 记录宿主实际行为。`inner=outer-2*border-2*padding`，gutter=min 3 列或最大真实编号的十进制位数 + 分隔空格；无编号不扣 gutter；正文 `inner-gutter-prefix` 必须 >=1。宽度不足先省略非关键 meta、缩短路径（保留 basename，中心省略）、缩小内部 padding、去掉 gutter、最后无框紧凑文本。不得为固定 header 造成溢出。每行样式复位，输出 pad 的两侧宽度合计不得超 W；宿主窄于单个宽字素时用安全占位符，不切 grapheme/ANSI。视觉行计算以 wrap 后结果为准，尾部截断跨行时保留样式重建。路径保持显示原始调用语义，不 resolve/symlink/stat，不使用 OSC hyperlink。

### 7.3 不可信文本与 ANSI

现有 pi-ui 0.5.0 sanitizeText 会移除 SGR 和 U+200D（L）；本切片需专用安全显示路径，不全局修改已发布 sanitizer 语义。统一解析/重建：代码/命令/路径/诊断只当普通文本，移除/转义控制序列，代码样式只能由已验证高亮器生成。Bash output.ansi=true 允许受限 SGR reset、bold、dim、italic、underline、标准/索引/RGB 前景色及相应 reset；不允许背景/终端命令的任意 passthrough。限制参数个数与范围，不直接输出原始控制序列。过滤 OSC（含 clipboard/title/hyperlink）、DCS、APC、PM、SOS、非允许 CSI、C0/C1、不完整序列及双向文本控制；保留 ZWJ、变体选择符和组合字符；CRLF→LF，单独 CR/BS 显示为静态可见分隔/转义，Tab 4-column tab stop；不模拟进度条覆盖或终端光标移动。对每个完整快照独立处理，截断不泄露半截序列。对高亮器生成的 ANSI 也验证允许集，逐视觉行、边框与切片 reset/reapply。ansi=false 同样执行过滤，只不解释颜色。错误路径使用相同 sanitizer 和宽度限制，最后固定安全提示。单元/fuzz/property 测试须检查所有 ESC 最终输出均为本地重建允许 SGR（不含宿主另行输出）。

### 7.4 资源上限、缓存及高亮

冻结首版安全预算（不是已测性能）：单工具当前派生缓存最多一个源快照的引用、一个高亮结果、一个当前宽度布局/卡片；无无界宽度 Map、无历史 partial 数组。原始数据由宿主持有，不能通过本计划限制其自身内存。高亮输入上限 256 KiB UTF-8 或 10,000 逻辑行，超出仅纯文本；显示扫描上限 1 MiB UTF-8、20,000 逻辑行、20,000 视觉行，超出明确显示 `UI safety limit — available result not fully shown`（不是 native truncation）。上限按安全字素边界截取，head/tail 根据模式选段；不得先全量生成无界派生数组再裁切。若超限无法准确计算隐藏量，用“部分内容未展示”而非伪造数字；错误诊断尽量独立保留，仍超限则说明并保留首尾安全片段。Expanded 受同一上限，不触发文件读取。对超长路径、参数、控制序列也施加同类有界扫描。资源上限可在实测后通过规格变更调整，首版不作为用户配置。

缓存 key 至少包含 tool kind、当前 row identity（由宿主隔离）、args/result revision、status、duration、notice、expanded、theme revision、config revision、width、outputPad、language、preview policy、showImages（如影响正文）。分离内容清洗/高亮与 width layout；只有确定输入或主题未变才复用，不能只用字符串长度。相同完整 key 重复 render 才叫 cache hit。若 Theme 对象可能原地变化，T0 验证公开主题事件/可用 fingerprint；未证实则该主题相关缓存失效，不访问内部字段。高亮由 Pi public `highlightCode`/公开语言识别入口注入；未知语言/异常/不支持时纯文本；流式 Write 如公开增量高亮不可验证，使用有界完整高亮或纯文本，不自建词法引擎。所有 renderer 默认不新增 timer/polling/process，依赖原生 partial/render 调度；render 只做同步计算。

## 8. 实施任务与门禁

任务编号为本计划唯一执行编号。Bash v1.1 的 B0–B6 内容映射到 T0-B、T2、T3、T6、T7，见附录 A。每项任务须提交测试、实现、证据及独立 Reviewer 结论。所有门禁初始 pending。

### T0 — 兼容性及最小探针

| ID | 操作与产物 | 通过条件 |
|---|---|---|
| T0-01 | 记录实际 CLI/SDK dist、Node/Bun、OS、安装包/lock、版本、源码指纹、exports、消费者实际解析路径 | 生成 docs/compatibility.md；tag 与本机差异显式登记 |
| T0-02 | 读取旧 hashline-diff 完整源码、配置、测试、依赖，记录全部 resolver/adapter 分支与旧视觉 fixture | 迁移输入冻结，未识别旧字段为阻断 |
| T0-03 | 创建隔离 PI_CODING_AGENT_DIR、临时 cwd/Session、公开 registerProvider 的本地确定性 provider，禁真实认证/外网/付费 | 真实 Pi PTY 可稳定重放工具调用；无用户数据污染 |
| T0-04 | 用一个测试 renderer 验证公共 resolver 顺序、next()、slots/state/lastComponent、outputPad、expanded、theme、历史、reload、非 UI、异常回退 | 记录公共机制及限制；各工具的 slot 选择进入自己的探针 |
| T0-05 | 确认公开高亮、语言识别、Theme/width API、实际 pi-ui exports；验证包入口和 peer 解析 | 不使用 private deep import，不加载第二套 Pi |
| T0-B1 | 真实 Bash fixture：成功/空/非零、审批等待/允许/拒绝/超时/取消、执行超时/取消、空首帧/多 partial/final 压缩、历史缺 duration | 按 §6.1 记录 args/content/details/context 和原生执行次数 |
| T0-B2 | Bash 行数截断 >2000 短行；字节截断 <2000 行且 >50KiB；>50KiB 单行；截断后超时/取消；低于原生上限且触发 compressor 的重复行 | 三类截断、纯文本诊断、shellCompressor 元数据真实可复现（实际阈值若漂移记录） |
| T0-B3 | OFF/ON（最小 renderer）保留 Gate/Compressor，验证最终执行、cwd、命令、审批结果和 model-visible final | allow=1，deny/timeout/abort during approval=0（限已验证 Gate 路径）；实际执行不可扩大 |
| T0-W1 | Write 实时 args snapshots：不完整、空、追加、替换、缩短、path 变化、final success/error/abort、历史 | 真实宿主的 argsComplete/executionStarted/slot/state 时序冻结 |
| T0-W2 | Write 成功/失败/覆盖/空文件/多行 Unicode/无尾换行，执行前后文件 bytes 与结果 OFF/ON 对照 | 内容只作参数预览，成功不提前，写次数/字节相等 |
| T0-R1 | Read 原生文本 offset/limit、空/EOF/非法、超长首行、行/字节截断、limit continuation、同形 notice 文件、Markdown、历史 | 确认正文边界和行号可证明/降级矩阵 |
| T0-R2 | Read 图片 showImages ON/OFF，模型支持/不支持图片，损坏图片仅返回文本说明，混合/错误及恰含同形图片说明的文本 | 保留原文、图片及 warning；诊断无源码编号；冻结 Read slot 方案 |
| T0-RH | §6.4 Hashline 0.1.2 的已改写、未改写、历史及残留原生截断字段情形 | 安全原文回退可复现，保留锚点和诊断；当前版本隐藏能力标 unsupported |
| T0-I | 用纯原生和完整用户栈两个隔离环境验证公共加载机制与同名竞争探针 | 旧扩展缺席、新工具关闭且无 Hashline/OMP/Powerline 时仍可启动；逐工具接入另行验收 |

隔离配置不能假定重定向 Shell Compressor：Bash v1.1 指明它直接读取用户 home 配置及可信项目覆盖。记录有效配置路径/值，保持真实用户配置只读；优先隔离 HOME（先证实 Pi/Bun 解析及 compressor 行为不变），否则使用只读实际配置且禁止写入，若无法安全隔离则阻断该组测试。测试命令使用本地 shell 内建、临时目标，网络关闭；命中真实 Gate 策略时通过 PTY 操作其现有 UI，使用确定性、无害、仅临时目录副作用的命令。不得关闭 Gate 来通过批准/拒绝测试。测试 provider 不得调用真实付费模型。

**门禁**：G0-Base 仅使用 T0-01、T0-03..05 和 T0-I 的公共 SDK、测试设施及包加载证据。T0-02 归 G1-Migration。G0-Bash 使用 T0-B1..3 和 Bash slot 证据；G0-Write 使用 T0-W1..2 和 Write slot 证据；G0-Read 使用 T0-R1..2、T0-RH 的原文回退和 Read slot 证据。可选 G0-ReadHash 需要另行证明未来版本的来源标记；按当前 0.1.2 的支持范围无需开启该门禁。各门禁以实际运行证据和独立 Reviewer 结论签署。

### T1 — 独立项目与旧 Diff 迁移

| ID | 实施 | 验收 |
|---|---|---|
| T1-01 | 新 repo/package、ESM、构建、typecheck、test、lint、pack、Pi entry；冻结 lock | 干净安装可启动，全部开关关闭不改变原生行为 |
| T1-02 | 按 §4.3 迁移旧 edit/hashline 实现、fixture、测试；逐字段保留旧 renderer | 旧 TUI 视觉、Hashline HTML call/Diff 与模型/执行行为等价 |
| T1-03 | 统一配置 schema、legacy dry-run 映射及备份/回滚说明 | 未知字段/冲突不丢失；新安装/迁移默认区分 |
| T1-04 | 静态 resolver、显式所有权、关闭与下游恢复 | 旧新分别独立，原生/自定义下游恢复 |
| T1-05 | native-only 无 Hashline、Hashline ON、完整现有栈 A/B；真实 PTY/pack | 迁移完成，Diff 无退化，无依赖旧包 |
| T1-06 | 发布 Migration candidate，记录旧新版本/commit 与生产切换步骤 | 用户批准后切换，失败可完整回滚 |

G1-Migration 依赖 G0-Base、T0-02 和 T1-01..06。通过后可独立进入 migration profile 的 T6/T7。实际生产启用由用户明确批准。

### T2 — pi-ui 共享能力

| ID | 实施 | 验收 |
|---|---|---|
| T2-01 | 审计 Panel/StatusLine/CodeFrame/exports，确认最小新增 API | 不重复实现、不改变现有 diff 契约 |
| T2-02 | ToolCard 组合标题、meta、状态、分区、fallback | 布局 property、snapshot、无重复边框 |
| T2-03 | CodeBlock + line numbers + preview + path label helper | head/tail、offset/gaps、wrap、CJK、emoji、未知编号 |
| T2-04 | OutputBlock 与安全控制序列解析、有限缓存 | §7 安全/资源上限测试；错误诊断保留 |
| T2-05 | 注入公开 highlighter，稳定前缀/纯文本降级 | 跨行词法与完整 oracle、theme/width 重排 |
| T2-06 | 为本次交付工具实现纯 View 与 Gallery fixture（无执行） | 使用共享组件、无宿主/业务依赖 |
| T2-07 | 实际 pi-ui 文档 delta、版本、exports、pack、旧消费者回归 | §3.2 双仓证据、无第二套 Pi runtime |

G2-Shared 按 Bash、Write、Read 分别出具验收记录。每项依赖 G0-Base、该工具通过的 G0 和它实际消费的 T2 能力，T2-06、T2-07 的 View、Gallery、发布与兼容回归也按当次交付范围验收。完整 profile 汇总三项。T1 迁移独立验收；旧 Edit 可在后续单独评估迁入 ToolCard，迁移阶段保留旧实现。

### T3 — Bash

| ID | 实施 | 验收 |
|---|---|---|
| T3-01 | 按 §6.1 编写 Bash adapter/状态、partial/final 归一化 | 全部 T0-B fixture、压缩 final、无虚假退出码 |
| T3-02 | BashView 命令、Output、tail、诊断、truncation、路径 | 6/12 视觉行默认，native truncation 与 UI collapse 区别 |
| T3-03 | 按 G0-Bash 冻结 slot 注册，独立开关、共享 state | 无重复命令/边框，原生 expanded |
| T3-04 | 流式、最终结果、resize、缓存、历史、异常 | latest final 权威，无历史 partial 泄漏 |
| T3-05 | 完整 Gate/Compressor OFF/ON，原生/自定义下游回退 | 执行次数、cwd、最终命令、schema/result/请求等价 |

G3-Bash=G0-Bash+G2-Shared 的 Bash 记录+T3 全部通过；生产启用另需 G1/G6/G7 对应 profile。不得改 Gate 包装后的 ToolDefinition。

### T4 — Write

| ID | 实施 | 验收 |
|---|---|---|
| T4-01 | Write adapter、参数类型及状态表、请求内容行计数 | 无成功提前、无文件重读、invalid/partial 正确 |
| T4-02 | WriteView CodeBlock、stream tail/final head、错误诊断 | 12/6 逻辑行、18 视觉行、真实展开 |
| T4-03 | 有界高亮缓存，追加/非追加/路径和主题变化 | 完整高亮 oracle 一致或明确纯文本 |
| T4-04 | G0-Write 选定 slot、final result 状态更新、历史及回退 | 单卡片/逻辑卡片；不丢诊断 |
| T4-05 | 真实文件 OFF/ON，写入/覆盖/失败/取消/历史文件被修改 | 实际执行次数、文件 bytes、模型结果等价 |

G4-Write=G0-Write+G2-Shared 的 Write 记录+T4 全部通过。未证明的执行阶段显示 pending/unknown；失败不得冒充未写入任何内容。

### T5 — Read

| ID | 实施 | 验收 |
|---|---|---|
| T5-01 | 原生结果 adapter，范围/正文/诊断/truncation 分离 | §6.3 全矩阵，notice 同形文本不误删 |
| T5-02 | ReadView CodeBlock、行号/gaps、head preview、unknown fallback | 12/24 预算，真实编号或明确无编号 |
| T5-03 | 可选未来 Hashline 版本的 Read adapter | 只有 G0-ReadHash 通过的来源和协议才可隐藏锚点 |
| T5-04 | 图片/混合内容、showImages、unsupported warning、图片处理失败的纯文本诊断、原生 slot | 保留媒体和警告，纯文本诊断无源码编号或高亮，图片不重复且不复制 base64 |
| T5-05 | 真实 Read OFF/ON（原生/Hashline）、历史、异常、回退 | 模型 content/hash anchors、schema、读取次数、结果等价；无额外 FS |

G5-Read=G0-Read+G2-Shared 的 Read 记录+T5-01/02/04/05，含 Hashline 0.1.2 保留原文的实测。可选 G5-ReadHash=G0-ReadHash+T5-03+已支持协议的专项测试。完整 v1.0 可按 §6.4 的当前支持范围发布。

### T6 — 生态集成与安全

| ID | 实施 | 验收 |
|---|---|---|
| T6-01 | 各工具独立开关、全部组合、竞争 resolver、历史/reload | 关闭返回原对象、未知工具不接管、无全局缓存 |
| T6-02 | Edit/Hashline 与旧迁移 fixture 对照，验证 Hashline HTML 导出；含 Read 的 profile 另验 Hashline hook | 原有工具、Diff 和导出完整，Read profile 的模型锚点不变 |
| T6-03 | Approval Gate、uv guard、Shell Compressor 真栈 OFF/ON | 安全 Reviewer 签署，不扩大现有 Gate 范围 |
| T6-04 | TODO、Prompt 当前 `footerMode: "none"` 及兼容模式 `inline`、Goal/Workflow/Subagent、审批草稿焦点 | 实际混合 pi-ui 版本均可用；不修改其他扩展 |
| T6-05 | RPC/print/headless、! / !!、嵌套工具路径 | 原生行为不变；非支持范围不接管 |
| T6-06 | 独立安装、无参考项目、无 Hashline 环境、依赖树/exports | 本 profile 已交付的原生工具可独立启用，旧包完全不加载 |

G6-Integration 按 release profile 分别出证据，覆盖交付工具和适用的共同回归；未来协议专项仅在该 profile 宣布支持时纳入。完整 profile 需要 G1/G3/G4/G5，当前 Hashline 0.1.2 以 §6.4 的原文兼容通过。原 pi-ui 主计划的 G4 权限最终绑定与取消要求保持有效。

### T7 — 性能、发布及回滚

| ID | 实施 | 验收 |
|---|---|---|
| T7-01 | 当次 profile 的 §9 fixture/PTY/行为等价及适用 Gallery | 测试可复现，全部交付能力通过，其他用例标为不适用此 profile |
| T7-02 | §10 benchmark 及混合消费者总预算 | 目标通过或明确阻断；不能擅改预算 |
| T7-03 | 真 pack/install、版本/lock、README/changelog、双仓文档对账 | 无旧扩展/第二套 runtime，实际 import 与配置有效 |
| T7-04 | 两级回滚演练、异常产物恢复、原生下游恢复 | 恢复步骤实测；无旧扩展新用户可回原生 |
| T7-05 | 安全及独立 Reviewer 最终签署，DoD/证据对账 | 无未解决阻断/高风险缺陷；限制公开记录 |

G7-Release 按 profile 依赖 G6 对应证据与 T7；完整交付须五种工具验收通过。若使用 slot C 降级，仍需符合 G0 冻结的视觉支持说明。不能把 fallback 原生 D 当作已完成该工具 UI。

## 9. 测试设计与证据

### 9.1 测试层次

| 层 | 必须执行 | 判定 |
|---|---|---|
| unit | adapter、config、迁移、状态、边界、preview、宽度、安全 | 确定性断言；错误输入不抛到宿主 |
| property/fuzz | Unicode grapheme、控制序列、极窄宽、随机行号、截断、缓存失效 | 所有行 ≤ W；无危险控制序列；不修改原始对象 |
| snapshot | 每工具状态、主题、折叠/展开、长路径、空内容、诊断、slot 降级 | 固定 fixture 与 width；旧 Diff 迁移 golden 不变（有理由的动态字段除外） |
| SDK integration | resolver chain、state、lastComponent、load order、config | public SDK；不 mock 掉关键宿主行为作为最终证据 |
| PTY | 真实 Pi + 本地确定性 provider + 隔离工作区 | 事件、屏幕、执行及模型结果共同证明 |
| packaging | npm tarball、实际安装路径、无旧包/Hashline 安装环境 | 不从 workspace 偶然解析；依赖契约正确 |
| performance | §10 | 固定环境，保留原始样本 |

### 9.2 必测 fixture 矩阵

| ID | 范围 | 场景与断言 |
|---|---|---|
| F01 | 所有 | 参数不完整、无 final、final error/success、duration 缺失、未知类型；不猜状态 |
| F02 | 所有 | 同一个 ID 的不同 Session、历史回放、reload、主题变化、expanded、outputPad=0/1/3（实际设置范围另验） |
| F03 | 所有 | width=0/1/2/10/20/40/60/80/120/160/240；长路径、CJK、combining、ZWJ、宽字素 |
| F04 | 所有 | ESC、OSC52、OSC8、DCS、CSI movement、C1、残缺序列、bidi、malformed SGR、CRLF/CR/BS/Tab |
| F05 | Bash | 无输出 `(no output)`、空首帧、多文本块、快照重复/缩短/替换、final 压缩、迟到 partial |
| F06 | Bash | 非零、超时、取消、拒绝、仅诊断、行/字节截断、首/尾超长行、fullOutputPath |
| F07 | Write | 空字符串、单行、有无尾换行、多个尾空行、CRLF、中文、HTML、invalid content、path 未完成 |
| F08 | Write | 流式 append/replacement/shrink、跨行词法、final error 后请求预览、final 无正文、历史文件已改变 |
| F09 | Read | offset omitted/0/1/120/negative/fractional；limit omitted/0/1/negative/fractional；EOF、空文件、非整数、超过限额首行 |
| F10 | Read | 真实 truncation.content、仅文本 continuation、同形 notice、混合内容、图片不支持告警、无 image block 或标记的图片处理失败说明、同形图片说明文本 |
| F11 | Read | Hashline 0.1.2 改写且保留原生 truncation details、跳过改写、原生同形锚点、历史与图片；原文和诊断完整，来源不明时无新增行号 |
| F12 | Edit/Hashline | 原有成功/失败/noop/summary/diff/长行/多文件（以旧支持范围为准），旧配置所有分支，Hashline 导出保留独立 call 与 Diff 正文 |
| F13 | 所有 | 100/1000/10000 行、超长单行、>1 MiB、>20k 行、无界 ANSI 输入、有界缓存；安全上限明确 |
| F14 | config | 全关闭、新安装、`editDiff.nativeEdit` 映射、`PI_HASHLINE_DIFF` 未设置/`0`/其他值、全局开关逻辑或、未知字段、冲突、关闭恢复原对象 |
| F15 | failure | adapter/slot/render 抛错、theme/highlight 失败、包入口损坏；安全诊断/两级回滚 |
| F16 | 可选 ReadHash | 仅声明支持新协议时运行，验证宿主来源标记、版本、非连续编号及拒绝未知或混合格式 |

F03/F04 均须验证每一最终行宽、控制序列白名单、样式复位；媒体宿主输出不纳入文本 sanitizer 的断言，但另验其原生行为。真实 PTY 选择 40/80/120/240 或宿主可支持的代表宽度；极窄纯布局覆盖全部。每种支持的 slot 方案分别跑 expanded/点击/历史/resize，不以一个 Bash 探针替代 Read/Write。

### 9.3 OFF/ON 行为等价

测试环境 A/B/C：A=旧 hashline-diff 锁定安装（仅迁移对照）；B=新版本全部 UI OFF；C=新版本对应 UI ON。另在 native-only 无 Hashline/Gate/Compressor 环境执行 B/C；完整用户栈 B/C 必须保留 Gate、Compressor、Hashline、TODO、Prompt 及已启用的其他扩展。各自独立进程、PI_CODING_AGENT_DIR、临时目录、Session。确定性 provider 记录所有模型请求与工具结果，禁止真实付费调用。

对照 ToolDefinition schema、来源、可调用性、args、执行器调用/副作用次数、实际命令/cwd、文件 bytes、宿主最终 content/details、模型后续收到的结果、错误标志、截断/压缩/anchor、取消/超时与批准拒绝。动态字段（时间戳、临时路径、随机工具调用 ID、耗时）必须先建立逐字段归一化规则并保存原始匿名证据，不过滤业务正文或错误类型。Read 次数以可验证的测试执行边界或文件 I/O 观察记录；若宿主无公开计数接口，使用测试环境外部观察或 fixture harness，不修改生产执行器。至少验证渲染器本身无任何文件 I/O。Gate 只在其已证明支持的路径验收 allow=1、deny/审批超时/审批期间取消=0；不宣称新 UI 改善 Gate 的安全性。

### 9.4 组合测试与回归

按 profile 覆盖全关闭、单工具和全部交付工具同时开启、Hashline 缺席、同名工具、resolver 前后顺序、旧扩展双加载拒绝、无效配置、重启/reload 与无 UI。迁移 profile 验证 Hashline `/export` 的 call 及 Diff，完整 profile 覆盖五工具的点击与快捷键、Read 图片及纯文本失败说明。测试用户 !/!! 和嵌套工具沿用既有路径。生态回归先用本机 Prompt `none`，再覆盖 `inline` 兼容配置，并检查 Approval 草稿与焦点、TODO、Goal/Workflow/Subagent。未安装的可选扩展登记为 not installed。

## 10. 性能预算与方法

以下为设计目标，非已测；延续 Bash v1.1 预算，扩大到新切片后仍须验证总预算。

| 指标 | 目标 | 测量边界 |
|---|---:|---|
| 首次渲染 P95 | ≤15ms | 80 列，100 行固定 Bash/Read/Write fixture，含首次清洗/高亮；不含执行 |
| 相同完整 key 热 render P95 | ≤2ms | 每工具 100 次以上，缓存命中定义 §7.4 |
| Resize P95 | ≤5ms | 固定 100 行，从 80 到 120 列来回，包含重新布局 |
| 新增冷启动中位数 | ≤20ms | 相对旧锁定安装/原生匹配栈，报告 migration、新 OFF、ON |
| 新增空闲 RSS 中位数 | ≤5MiB | 同一 ready/idle 时点，整体新包增量而非每工具可相加 |
| 新增模型请求/Token | 0 | 相同确定性 provider 请求与工具结果 |
| 新增执行/常驻进程/后台轮询 | 0 | UI 不新增执行器、timer、外部进程 |

使用同机、同 Pi/Node/OS/theme/config、相同 fixture、交替 A/B/C 顺序；至少 20 次冷启动和每组 100 次热样本；记录 median、P95（nearest-rank）、样本数、测试命令、机器及原始数据。冷启动从进程启动到首个可交互提示符，RSS 同一时点；报告绝对值及差值。分离纯组件 render、宿主刷新、实际执行耗时。1000/10000 行、超长单行、连续 1000 次 partial、至少 1000 个历史工具行、Session 切换/reload 做压力样本，报告时间/RSS 趋势；宿主持有历史数据的正常增长与派生缓存泄漏分开比较，不能以 GC 未运行推断泄漏；可用同环境受控 GC 测试辅助。无每帧定时器；非追加大流式 Write 不因高亮反复构建无界历史。

整体继续对照 pi-ui 主计划 v1.5 P5-03 的实际总预算（启动中位数≤50ms、RSS 中位数≤15MiB 及对应渲染指标；实施时核对原文和已批准基线）。本切片 20ms/5MiB 不与 Prompt/其他切片预算简单相加。迁移 profile 以旧扩展对照；full profile 同时测原生 matched-stack 与旧扩展 matched-stack，明确各自差值。目标未达则定位热点、减少无必要抽象、保持 native fallback；不得把目标改为实测值来通过门禁。独立 Reviewer 复核方法与样本。

## 11. 交付、回滚及风险登记

### 11.1 交付清单

- pi-tool-ui 独立 repo、锁文件、可安装 npm tarball、实际发布版本、兼容矩阵、README、CHANGELOG、许可证。
- pi-ui 新增组件和 View、稳定 exports、兼容测试、发布包与版本；不改变旧消费者的依赖锁。
- dotfiles 仅保留新包配置及迁移说明；旧 hashline-diff 不再在活动路径中。不得直接删除用户未备份的源码。
- `docs/implementation-plan.md`、`compatibility.md`、`implementation-status.md`、`migration.md`、`release-evidence.md`；pi-ui 配套文档与 commit 对账。
- 匿名化 fixture、PTY transcript/截图、OFF/ON 对照、性能原始样本、独立 Reviewer 报告；不记录真实认证、敏感路径、真实用户代码或命令日志。

### 11.2 风险登记（初始）

| ID | 风险 | 缓解 | 阻断条件 |
|---|---|---|---|
| R01 | 自定义 shell 与 call/result slot 无法稳定组合 | A/B/C/D 探针 | 对应 G0 未通过 |
| R02 | 同名 resolver 竞争，无法自动辨认 owner | 显式配置、隔离、禁止双加载 | 未知竞争者未清除 |
| R03 | 旧 Diff 迁移丢配置/行为 | 完整源码清点与旧/新等价 | G1 失败 |
| R04 | Hashline 来源不可辨识，残留原生 metadata 造成误剥 | 0.1.2 保留原文；未来协议须证明来源 | 原文回退失败阻断 Read；未来专项失败只阻断对应隐藏能力 |
| R05 | Read notice 与真实正文同形 | 无证据不剥、不编号 | 误删/伪造行号阻断 Read |
| R06 | 图片重复/丢 warning | 原生 slot 探针与 C 回退 | G0-Read/G5 失败 |
| R07 | Shell Compressor final 与 partial 不同 | final authoritative | 旧 partial 覆盖 final 阻断 Bash |
| R08 | UI 绕开或改变 Gate | 不注册工具，不调用 execute；真实 OFF/ON | 安全等价失败阻断发布 |
| R09 | Write 流式高亮退化/词法错误 | 有界缓存、oracle、纯文本回退 | 性能或内容错误未解决 |
| R10 | ANSI/宽度/控制注入 | 白名单重建、grapheme 测试 | 任一不安全输出阻断 |
| R11 | peer 解析/重复 runtime | 实际 pack、干净安装与加载路径 | 包启动或依赖失败 |
| R12 | 本机版本与公开源码漂移 | T0 指纹、真实 dist 优先 | 未验证版本不声明支持 |
| R13 | 配套文档只生成未进仓库 | 双仓 commit 对账 | G2/T7 发布未关闭 |
| R14 | 多工具叠加超过总预算 | 整体 profile benchmark | 预算未达不发布该 profile |

### 11.3 回滚演练

按 §4.3 真实演练：关闭单项→重启；关闭全局→重启；损坏/不可导入包→恢复原锁定包或原生；迁移回旧扩展仅用户主动选择，绝不能在新包安装时自动依赖旧扩展。每次回滚检查实际工具执行、原生/下游 renderer、原有 Edit、审批及 Prompt 正常。备份和恢复保留用户配置，测试环境不写真实 home。禁止把单条 render 异常当作权限决策或失败工具执行。Release README 明确实际支持版本、各工具 default-off、迁移步骤、已知降级和卸载方法。

## 12. 执行 DAG、任务所有权与门禁状态

```text
G0-Base + T0-02 -> T1 -> G1-Migration -> migration profile T6/T7 -> optional production switch
G0-Base + G0-Bash  -> T2 Bash  -> G2-Shared Bash  -> T3 -> G3-Bash
G0-Base + G0-Write -> T2 Write -> G2-Shared Write -> T4 -> G4-Write
G0-Base + G0-Read  -> T2 Read  -> G2-Shared Read  -> T5 -> G5-Read
G1 + delivered tool gates -> profile T6 -> G6 -> profile T7 -> G7
G0-ReadHash -> T5-03 -> G5-ReadHash (optional future protocol)
```

T1 和 T2 可在接口及文件所有权分离时并行；T3/T4/T5 可在各自 G0 和共享能力冻结后并行。共享 `src/index.ts`、配置 schema、resolver 和 package/lock 由单一集成任务负责；子任务通过独立 adapter/renderer/fixture 文件提交，不同时编辑共享入口。pi-ui 公共 API/exports 由共享组件负责人冻结，其他任务仅消费。使用独立 worktree（如现有 workflow 支持）时记录基线 commit、文件范围、合并顺序、冲突及测试；合并后重新跑跨切片测试。每项 Coding 任务实施 TDD（先失败测试→最小实现→回归），独立 Reviewer Subagent 做规格和质量审阅；安全事项另外核对授权边界。Reviewer 未完成/失败不视为通过。主 session/负责人汇总门禁，禁止子任务擅自发布或变更生产配置。

`implementation-status.md` 每项采用：

```text
ID | pending/running/blocked/passed | owner | baseline SHA | implementation SHA
  evidence paths | commands/environment | actual results | limitations
  independent reviewer identity/result | follow-up
```

初始所有 G0–G7 及子门禁 pending；已提供的 L/S 证据可关闭对应静态事实，不代替动态门禁。每个 release profile 有独立通过记录，不将部分能力发布标为全部完成。依赖变化、SDK 升级、resolver slot 变化、配置/schema 或权限路径变化需重新打开相关门禁及下游回归。

## 13. Definition of Done（完整 v1.0）

| ID | 最终验收 | 证据/门禁 |
|---|---|---|
| A01 | 只替换 renderer，保留所有 ToolDefinition/execute/schema | G0/T6 OFF/ON |
| A02 | 独立 pi-tool-ui npm 包，旧 hashline-diff 不加载、不依赖 | G1/G7 真实安装 |
| A03 | Edit/Hashline TUI 与 Hashline HTML 迁移无退化，配置完整映射 | G1 golden + parity |
| A04 | 无 Hashline 环境四原生工具正常；可选 Hashline 兼容 | G6 native-only |
| A05 | 每工具卡片符合冻结 slot 方案，无重复命令、正文、边框 | 各 G0/G3–G5 PTY |
| A06 | Bash partial→final、compressor、truncation 正确 | G3 fixtures |
| A07 | Bash 命令、状态、耗时可信，退出码未知留空 | G3 |
| A08 | Write 参数流式尾部/完成头部、真实行数及失败诊断 | G4 |
| A09 | Write 不重读文件，模型/文件 bytes/执行次数等价 | G4 OFF/ON |
| A10 | Read offset/limit/真实行号与截断；不误删同形文本 | G5 |
| A11 | Hashline 0.1.2 原文与锚点保留；未来版本隐藏能力按已验证协议单独验收 | G5；未来协议另附 G5-ReadHash |
| A12 | 图片、混合 content、unsupported warning 及纯文本图片处理诊断保留 | G5 |
| A13 | 所有文本 ANSI 安全、CJK/宽度/预览及安全资源上限 | G2/G6 fuzz/property |
| A14 | 原生 expanded、历史、reload、theme、下游回退 | G6 PTY |
| A15 | Gate 批准/拒绝/超时/取消的既有授权与执行不变 | G6 安全 Reviewer |
| A16 | Shell Compressor 最终模型结果与原生行为一致 | G6 OFF/ON |
| A17 | TODO/Prompt/Goal/Workflow/Subagent 与原有生态回归 | G6 实际安装矩阵 |
| A18 | 无 UI、! / !!、嵌套工具不改变原生行为 | G6 |
| A19 | 各工具独立开关；新安装默认关闭；冲突不接管 | G1/G6 |
| A20 | 无 OMP、Powerline、旧扩展、Hashline 必需依赖，无第二套 Pi runtime | G7 dependency audit |
| A21 | 无新增模型请求/Token/执行/后台轮询，性能及整体预算达标 | G7 benchmark |
| A22 | 包、配置、两个仓库文档/版本/commit 对账 | G7 pack + docs |
| A23 | 两级回滚实测成功 | G7 rollback |
| A24 | 全部已启用工具独立 Reviewer 通过，无未关闭阻断/高风险缺陷 | G7 sign-off |

A11 以 Hashline 0.1.2 的原文兼容作为当前 v1.0 验收。A05 可用经 G0 验证的 C 外框；D 不计入交付能力。Migration profile 的其余 A 项标为 not in profile。Full release 的每项当前支持能力均须有测试证据。

## 附录 A — Bash v1.1 审阅契约继承对账

以下对照表记录 Bash UI v1.1 的契约如何迁入 Tool UI。

| 原 v1.1 | 本文对应 | 处理 |
|---|---|---|
| §2 本机真实版本、resolver、state、outputPad | §2、§5、T0 | 保留；公开 tag 与安装包对应待验 |
| §3.2 CodeFrame diff 契约、无公共 ToolCard、注入 highlightCode | §3、§7、T2 | 保留旧 API；因新增消费者提取共享能力 |
| §3.3 旧 dotfiles 承载、显式开关、不能判断下游归属 | §4、T1 | 仅替换宿主为新包；所有权约束保留 |
| B0-01 隔离配置、Shell Compressor 独立 home 读取 | T0-03、§8 隔离说明 | 保留并明确安全失败条件 |
| B0-02 三类截断、空 partial、压缩 final、历史 | T0-B1/B2、F05/F06 | 保留 |
| B0-03/04 shared state、零行 result、slot fallback | §5、T0-04、G0-Bash | 公共机制与 Bash slot 分别验证 |
| B0-05 Gate 确定性 provider/执行次数 | T0-B3、§9.3 | 保留 |
| §5.2 structuredContent 不可见、duration 为工具调用时间、cwd | §5.3、§6.1 | 保留 |
| §5.3 executionStarted 非进程启动、空首帧 running、历史 unknown | §5.3、§6.1 | 保留 |
| §5.4 final compressor authoritative | §5.2、§6.1、T3 | 保留 |
| §6.2/3 6/12 visual rows、truncation 与 UI collapse、文本错误 | §1.2、§6.1 | 保留 |
| §6.4 `(no output)` 不误删 | §6.1 | 保留 |
| §6.5 图片宿主、展开快捷键 | §5/§6/§9 | 保留 |
| §7 sanitizer 会移除 ZWJ、SGR 重建、完整快照 | §7.3 | 保留；统一安全显示 |
| B1/B2/B3/B4 | T2/T3、§5–7 | 保留任务语义、增加共享消费者 |
| B5 Gate/uv、无 UI、嵌套调用、零依赖 | T6 | 保留 |
| §13 config bashUi default-off、整数范围、唯一诊断 | §4 | 一次性映射到 toolUi.tools.bash |
| B6 benchmark、实际 pack、旧下游恢复 | T7/§10/§11 | 保留；扩充独立包迁移 |
| §19 docs 与 dotfiles exclude | §3.2、§11、§12 | 文档移至受版本控制新仓，旧文件不作为发布基线 |

## 附录 B — 实施 Agent 启动指令

1. 不进入 T2/T3/T4/T5 产品实现之前先执行 T0 对应探针。先在隔离环境记录本机实际版本、旧扩展完整源码和配置；以真实 SDK 为准。
2. 建立 `implementation-status.md`，为每个门禁登记证据路径；不使用旧扩展或参考项目作为新包依赖。
3. 优先完成 T1 无行为变化迁移，独立审查后才允许用户切换。迁移 release 不等待其他三种工具。
4. 各新工具按 G0→共享组件→adapter→renderer→回归的顺序开发。不要为追求圆角或无 anchor 视觉而重写执行链或假设不存在的数据。
5. 使用真实 Pi PTY、确定性 provider、临时文件和原有 Gate/Compressor 验证。无网络付费请求，不写生产配置。
6. 每项任务 TDD 和独立 Reviewer；门禁失败记录原因及安全降级。对无法通过公开 SDK 实现的能力停止接管，而非使用私有 API。
7. 在实际发布包验证、依赖审计、两个仓库文档对账和回滚通过之前，不宣布完整 v1.0 完成。

**当前状态：本机静态审阅完成，可进入 T0。完整旧扩展迁移证据、真实 PTY、打包安装及独立门禁审查仍待执行。**
