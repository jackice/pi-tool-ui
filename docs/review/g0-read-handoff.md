# G0-Read / G2-Shared(Read) / G5-Read 评审交接

## 目标
验证 Read 接管只改变展示，不改变执行、路径、字节、权限、错误与图片生命周期；判定 G0-Read、G2-Shared(Read) 是否可签署，G5-Read 还缺什么。

## 范围
- `src/adapters/read.ts`、`src/renderers/read.ts`、`src/integration/resolver.ts`、`src/index.ts`、`src/config.ts`
- `tests/unit/read-adapter.test.ts`
- `tests/pty/read-t0.py`、`read-t0-provider.ts`、`read-history.py`、`read-view-pty.py`、`read-product-ab.py`
- `docs/evidence/read-t0.json`、`read-history.json`、`read-view.json`、`read-product-ab.json`
- `docs/implementation-status.md`
- pi-ui `src/views/read.ts`、`tests/unit/read-view.test.ts`（0.6.7）

Out of scope：Write streaming/highlight、T6 Hashline A/B、发布与生产切换。

## 计划依据
- `../dotfiles/docs/pi-tool-ui-implementation-plan-v1.0.md` §4/§6.3/§8 T5、G0-Read、G2/G5 Read。
- pi-ui `docs/implementation-status.md` 0.6.7 ReadView。

## 实现摘要
- `adaptRead`：原生路径/范围编号；非法 offset 不编号；Hashline 原文回退；image/mixed 不编号；truncation 字段白名单；error 原文。
- Read renderer：仅替换 `read.renderResult`；任何 image block 回退原生；缓存含 content/details/expanded/isError/args/config/theme；异常回退。
- `ReadView`：真实行号、head 12/max 24、truncation 提示、原文回退，不臆造总行数。
- 刻意不做：Hashline 锚点隐藏（0.1.2 保留原文）、图片渲染接管、Write 改动。

## 验证证据
- pi-ui `npm test`：159 passed；产品 `npm test`：52 passed；typecheck/lint/build 通过。
- `PI_BIN=/tmp/pi160/node_modules/.bin/pi uv run --with pyte python tests/pty/read-t0.py` → 通过（含 unsupported/损坏/mixed）。
- `read-history.py` → 历史 content/details 一致。
- `read-view-pty.py` → 文本编号/截断/Markdown 卡片，图片原生回退。
- `read-product-ab.py` → ON/OFF content/details 一致、各执行一次；文本 ON 卡片、OFF/图片无卡片。

## 已知风险
- 行号起始基于“默认 offset 1、显式正整数”协议；Hashline/自定义 read 文本无锚点时按原文显示。
- truncation 的 total/output 语义按字段显示，未声明为文件总行数。
- T5-03（Future Hashline 锚点隐藏）与 T6 Hashline/原生 A/B 未做；G5-Read 不应因本次签署。
