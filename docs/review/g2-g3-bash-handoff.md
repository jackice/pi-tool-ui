# Review Handoff — G2-Shared / G3-Bash

## 目标

评审 pi-ui Bash 共享组件与 pi-tool-ui Bash adapter/renderer，判断 **G2-Shared（Bash）** 与 **G3-Bash** 是否可签署。范围仅顶层模型 Bash。

## 范围

- pi-ui `0.6.0`（tag `v0.6.0`，已发布 npm next）：`ToolCard`、`CodeBlock`、`OutputBlock`、`BashView`。
- pi-tool-ui HEAD（本次提交）：`src/adapters/bash.ts`、`src/renderers/bash.ts`、resolver/index 接线。
- 证据：`pi-ui/tests/unit/{tool-card,code-block,output-block,bash-view}.test.ts`、`examples/gallery.ts`；`pi-tool-ui/tests/unit/{bash-adapter,bash-renderer}.test.ts`、`tests/pty/{bash-view-pty,bash-product-ab,bash-history-product}.py` 与 `docs/evidence/bash-{view,product-ab,history-product}.json`。

## 已验证

- BashView：命令 6 行 head、输出 12 行 tail、截断/全量路径提示、状态 glyph、耗时；宽度矩阵 0–240 含 CJK/emoji/长命令无溢出；展开后显示全部 20 行。
- 安全 OutputBlock：SGR 白名单，剥离 OSC/CSI/控制符/bidi。
- Adapter：success/error/running、空输出、truncation、fullOutputPath、非字符串命令；不推断 exitCode。
- Renderer slot C：保留原生 shell/call，仅替换 result；内容/展开/主题变化换新视图，相同 key 复用；adapter 抛错回退原 renderer。
- 产品 PTY：成功/截断/错误/展开卡片；Gate+Compressor 栈 ON/OFF 各执行 1 次，模型结果一致，`shellCompressor` 1000→153；历史新/旧会话分别显示/省略耗时。
- Edit/Hashline 回归仍等于 golden。

## 限制

1. 未做真实 PTY 窗口 resize，只有 BashView 宽度矩阵。
2. 未单独跑 Bash 产品 renderer 的自定义下游回退（Edit 已有）。
3. 主题仅默认；未跑 light/dark PTY 对照。
4. `cwd` 不显示（默认 showCwd=false），配置字段尚未接入 renderer。
5. 未覆盖 `!`/`!!`、codemode、非顶层 Bash。

## 请 reviewer 输出

- G2-Shared（Bash）与 G3-Bash 的 passed/blocked，逐项引用证据。
- 若 blocked，列最小动作；若通过，明确 T6/T7 仍需验证项。
