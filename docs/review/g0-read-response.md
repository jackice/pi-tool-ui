# G0-Read 首轮评审响应

首轮结论：G0-Read/G2-Shared(Read) block。以下按 finding 处理。

| # | 结论 | 修复与证据 |
|---|---|---|
| 1 续读提示/limit=0 编号 | 成立 | 识别末尾原生续读提示，提示行与前导空行不编号；纯提示回退原文；`truncation.outputLines` 限定编号边界。`read-adapter` 新增 range/zero/outputLines 测试。未采用“有 limit 就整段不编号”，因为提示可识别且正文起始已证；若出现未知提示格式则回退原文。 |
| 2 图片纯文本诊断 | 成立 | `text.startsWith('Read image file [')` → `lines: []`、`contentKind: 'unknown'`、原文回退；覆盖 processImage 失败与同形文本。 |
| 3 空文件空白行 | 成立 | 空 content 返回 `lines: []`；新增单测与 PTY。 |
| 4 T0-R2 证据 | 成立 | 新增合法 IHDR/损坏 IDAT 的 processImage 失败 fixture、`imageUnsupportedByModel: 'local'`、showImages OFF 原生回退、同形文本；`read-t0.json`/`read-view.json` 更新。 |
| 5 limit 矩阵 | 成立 | 新增 limit=1/-1/1.5；PTY 断言续读提示无 gutter。 |
| 6 产品探针 | 成立 | `read-view-pty.py` 增加 range/zero/empty/longline/process_fail/text_like_image/showImages OFF，并断言提示行无数字。 |
| 7 历史回放 | 成立 | 回放不带 prompt、修改原文件、断言无 `tool-execution` 且显示保存的 alpha；`read-history.json` 记录 `reexecuted:false`。 |

非阻塞项：pi-ui README/contract 补 `ReadView`；ReadView 增加 null-number 与空模型测试；`highlight`/`hideHashAnchors` 仍未消费，按 T5-03/T2-05 保留 unsupported。

验证：pi-ui 161 单测；pi-tool-ui 55 单测；typecheck/lint/build；read-t0、read-history、read-view、read-product-ab 全通过。
