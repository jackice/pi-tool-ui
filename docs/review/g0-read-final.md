# G0-Read 最终复审响应

第三轮结论：G0-Read signed、G2-Shared(Read) signed、G5-Read 剩两项证据。

已补：
1. `read-view-pty.py` 增加 `image_unsupported`（vision=0）产品用例：无 Read 卡片，原生显示 placeholder 警告；`read-show-images.py` 证明 showImages 上下文 false/true。
2. `read-hashline-ab.py` 加载 `@jackice/hashline 0.1.2`，range/truncated OFF/ON：content/details 一致、各执行一次、锚点原文保留、ON 卡片/OFF 原生。
3. ReadView 隐藏计数排除 null-number 元数据，pi-ui 0.6.8 发布并由产品使用（56 单测）。

证据：`read-view.json`、`read-show-images.json`、`read-hashline-ab.json`、`read-product-ab.json`、`read-t0.json`。

## 第四轮修复

- pi-ui 0.6.9：全 null lines 走无行号 CodeBlock head 12/24，1000 行回归测试。
- 产品升级 0.6.9；`read-view-pty` 增加 long `negative_limit`，断言折叠卡片不含 line 13 且 ≤30 行。
- Hashline A/B 断言并记录 `hashline_version: 0.1.2`。
