# Review Handoff — G0-Write / G2-Shared(Write) / G4-Write

## 目标

评审 Write 的 T0、共享 WriteView、adapter/renderer 与产品行为，判断 G0-Write、G2-Shared(Write)、G4-Write。

## 范围

- 仓库 pi-tool-ui HEAD 以最新提交为准；pi-ui 0.6.5（WriteView）。
- 证据：`tests/pty/write-cases.py`、`write-stream.py`、`write-view-pty.py`、`write-product-ab.py`、`docs/evidence/write-*.json`、`tests/unit/write-adapter.test.ts`、pi-ui `write-view.test.ts`。
- 计划 §6.2、§8 T0-W、T4、§12。

## 已验证

- 成功/空/Unicode/覆盖/错误写入 bytes 与 final 一致；各执行一次。
- 低速 faux 流产生 10 次 `argsComplete=false` 参数快照，final 内容正确。
- `adaptWrite`：path/content/CRLF/lineCount/argsComplete/error notices。
- `WriteView`：head 6、行号、错误隐藏正文；产品 PTY 路径/正文各一次。streaming tail 未交付（T4-02 blocked）。
- 产品 OFF/ON：bytes/args/result 一致、各 1 次、ON 有 Write 卡片、OFF 无。
- slot C：保留原生 call/path，仅替换 result。

## 限制

1. `write.highlight` 未实现，当前应按 unsupported 处理（T4-03 pending）。
2. 未做真实 expanded PTY（仅单测）、resize、历史回放与主题。
3. 未做 `!`/`!!`、codemode、非顶层 Write。
4. 未验证磁盘最终 bytes 与 args 在异常中断下的部分写入语义。

## 请 reviewer

逐项 T0-W1/W2、T2-06(Write)、T4-01..05、G0-Write、G2-Shared(Write)、G4-Write 判定；列最小阻断。
