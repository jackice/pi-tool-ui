# T0 兼容性基线

- Pi 1.6.0（Bun 全局安装），Bun 1.3.14，Node v25.9.0，macOS 26.7.3 (25G342) arm64。
- 实际 CLI：全局 `@earendil-works/pi-coding-agent/dist/bundle/cli.js`。SHA-256 `e79626f2dd6f94aa45d30f3fa63cd84319a6eefcd150b353cfaf274366926774`。
- SDK 声明 `dist/index.d.ts` SHA-256 `b896b72effa2ee729087181a294cf93c45abc323daad2aadbda5f449acafa54a`；`dist/core/extensions/types.d.ts` SHA-256 `3c1728cdf8f9255273047cb260fddb6827637c55eb4edfe06f78f3e18823afd7`。公开包根导出 `highlightCode`、`getLanguageFromPath` 和 `Theme`，尚未做高亮行为验收。
- GitHub Commit API 对计划固定的 Pi commit、两个 OMP commit 均返回 200；本地 OMP checkout 不含这两份 commit。源码树与文件指纹、Pi 已安装产物与 commit 的对应关系尚未校验；安装 manifest 无 `gitHead`。

## 依赖漂移

| 消费者 | 实际已安装 | 位置（相对各自安装根） |
|---|---|---|
| 旧 hashline-diff | pi-ui **0.5.1**，锁文件声明 **0.4.2** | 扩展内 `node_modules/@jackice/pi-ui` |
| Prompt 0.2.1 | pi-ui 0.5.0 | Pi npm 根的 `node_modules/@jackice/pi-ui` |
| Approval 0.1.6 | pi-ui 0.4.2 | 它自己的 `node_modules/@jackice/pi-ui` |
| TODO 0.1.2 | pi-ui 0.4.2 | 它自己的 `node_modules/@jackice/pi-ui` |
| Hashline | 0.1.2 | Pi npm 根的 `node_modules/@jackice/hashline` |

Registry 实测 `@jackice/pi-ui` 的 `latest=0.4.2`、`next=0.5.1`。实际旧扩展所装 0.5.1 根产物 SHA-256 `3b1f274107e72980dbf3f14207e330f43ca03c247ef37464c176dabf440e54c4`。所见 pi-ui 安装的包导出键一致：`.`、`./diff`、`./views/approval`、`./views/edit`、`./views/todo`；这不证明根导出的符号完全一致。迁移对照需要区分锁定安装 0.4.2 与实际安装 0.5.1，不擅自重装生产目录。

## 旧 Diff 迁移输入

实际入口解析至 dotfiles 的 `pi/.pi/agent/extensions/hashline-diff/index.ts`。该目录最近变更 commit `53ff1857930fb0b2a49c01077dc90d047df105fe`；两个源码文件的最近编写提交作者为 jackice，扩展 manifest 未声明 license。未发现该目录内有跟踪的独立测试。生产全局设置 `editDiff.nativeEdit=true`，未见 `toolUi` 或 `bashUi` 键；当前主题为 catppuccin-mocha。Hashline 除非启动时环境值恰为 `0`，否则启用。

| 文件 | SHA-256 |
|---|---|
| `index.ts` | `7ca9f1e56aa59c5b3d6cc6ecbe6cafa7cfde1be1fd4e8db43f59737b037be159` |
| `native-edit.ts` | `008ac830ff41faa3bda21900fcd61958c5faee96ad11a3b1ce0dfbd1944b4d4c` |
| `package.json` | `6f932c4a810781dfcd0fd6602ea9d742d1428fc2debc448a10e268c80fd83dc1` |
| `package-lock.json` | `af622b38e601bc2d4b72ba434186f187c0f3d29eb5aec70c2bcbe3409ca51929` |

旧 resolver 先调用 `next()`；无下游、未选中时返回原对象。Edit 保留 shell 和 call，只在非 partial、非 error 且 adapter 识别单文件 unified patch 时自绘；空改动、不同文件头、畸形 hunk 等回退。Hashline 改用 `self`，保留 call，非 partial 时交给 pi-ui 的 `adaptHashlineDetails`。两路均使用 SDK 行级 state 缓存；失败时交原 `renderResult`，缺失时以文本块换行拼接。匿名旧视觉 fixture 和 HTML 对照尚未采集。
