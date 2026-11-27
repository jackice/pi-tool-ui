# G6 集成评审交接

## 目标
判定 Bash/Write/Read + Edit/Hashline 迁移在真实栈中的集成门禁是否可签，或列出最小缺口。

## 范围
- `src/index.ts`、`src/integration/resolver.ts`、各 adapter/renderer
- `tests/pty/{integration-matrix,headless-ab,rpc-ab,export-parity,export-write-read,security-stack,security-compressor,mixed-versions,pack-artifact,user-bash}.py`
- `docs/evidence/{integration-matrix,headless-ab,rpc-ab,export-parity,export-write-read,security-stack,security-compressor,mixed-versions,pack-artifact,user-bash}.json`
- `docs/implementation-status.md` T6 表

## 已验
- Bash/Write/Read 同会话 OFF/ON content/details/files 一致、卡片互斥、`/reload` 不重跑。
- `--print`/RPC Read/Write 一致；`!` 用户 Bash 不被接管。
- Edit/Hashline 预渲染 HTML 一致；Write/Read 模板导出正文保留。
- Gate/uv/Compressor 与产品同开安全签；Prompt/TODO 混合 pi-ui 0.5.0 共存。
- 打包 tarball 干净安装，无第二套 Pi runtime；Bash/Write/Read 卡片。

## 已知限制
- T6-01 未枚举 2^N；已补重复加载单卡片、三工具矩阵、resolver 单测。
- T6-05 已补 `--print`/RPC Bash、`!`/`!!`；nested 子会话不进入父 renderer（架构事实），未单独 PTY；未知/无下游 resolver 有单测。
- T6-06 无 Hashline 环境下 Bash/Write/Read 卡片；Edit 由 tarball-matrix/G1 覆盖。

## 问题
1. 上述限制是否阻止 G6 签署？
2. 若不阻止，给 G6 sign；若阻止，列最小证据。
