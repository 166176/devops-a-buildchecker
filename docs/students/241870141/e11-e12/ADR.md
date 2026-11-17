# ADR：集成接口决策

编号、日期、作者：ADR-E11E12-01 / 2026-11-17 / 241870141

问题：BuildChecker 的全量图与 EChecker 的增量扫描如何衔接，DRAFT 的修复输入从哪里来，异步任务如何保证可重复与可追溯。

候选方案：

1. 让 EChecker 每次自己重跑 strace 全量检测——最准确，但每次都要 clean build，失去“复用”的意义，也偏离 EChecker 的增量前提。
2. 只用 EChecker 的 `scan()`，不接入 BuildChecker——实现简单，但接线未验证，报告里“全量/增量一致”就没有独立来源。
3. 接入 BuildChecker 全量图作为历史缓存初值，之后用 `scan()` 走增量，并与目标提交的全量结果对照——本次采用。

采用方案与原因：

- **历史缓存来自真实全量图**：`pipeline.py` 先对 base 提交跑 `buildchecker.full_check`，把 `actual-graph.json` 投影成 main.o/helper.o 的 `actual`，并与 `lab.scan` 的 GCC 观测**断言相等**；相等才写入 `baseline-cache.json`。这样“复用”的起点有独立工具背书，不是自证。
- **增量与全量双跑对照**：目标提交既跑 `scan(target, old)`（增量），也跑 `full_check(target)`（全量），只比较对象目标（main.o/helper.o）的发现集合；比较范围限定，避免把 `app` 链接目标混进来。
- **E12 的修复输入取自本轮增量报告**：`repair` 阶段消费 `incremental-check.json` 并通过 `artifact` 的 `sha256` 重新校验后再解析，避免“固定 MD 文件”让联调变成假接线。
- **统一信封 + 内容哈希**：`schema_version=e11e12-1`、`kind`、`commit`、`status`、`data`、`artifacts[]`；消费前校验 schema、commit、kind 与哈希，任一不符即 `SCHEMA_MISMATCH`/`STALE_REPORT`/`ARTIFACT_TYPE_MISMATCH`/`ARTIFACT_HASH_MISMATCH`。
- **异步 API 单工作线程 + 幂等键**：`ThreadPoolExecutor(max_workers=1)` 避免并发 `git clone`/`docker build` 争用；键映射 `(request_hash, job_id)`，同键同输入返回同任务，同键异输入返回 409；重启时把未完成任务标 `SERVER_RESTARTED`，已完成任务保留可查。

输入输出字段：

| 阶段 | 输入 | 输出 |
| --- | --- | --- |
| full-check | base 提交、项目路径 | `baseline-full/{trace,make-db.txt,actual-graph.json,findings.json}` |
| incremental-check | base 缓存 + target 提交 | `incremental-report.json`（`actual/declared/findings/added/resolved/reused/refreshed`） |
| fixed-md（E11-B） | 固定报告（commit 必须等于 target） | `fixed-md-input.json` |
| repair | 增量或固定 MD 报告 | `candidate.patch`、`repair-plan.json` |
| recheck | patch + 项目 | `validation/validation.json`、`final-full/findings.json` |

兼容性与测试：

- 契约测试 10 项（参考实现）+ 本人新增 4 项 = 14 项，`Ran 14 tests ... OK`。
- 新增：产物哈希/相对 URI、缺失 `schema_version`、空白幂等键拒绝、重启后未完成任务标记。
- 修复：`server.py` 键校验改为 `key.strip()`；不改对外字段，仅收紧无效输入。

代价与覆盖范围：

- 代价：E12 每轮仍要跑一次基线全量与一次目标全量，耗时高于纯增量；样例单轮约数十秒，可接受。
- 覆盖：双 C 源文件 + `config.h` + 显式 Make 规则；其他项目结构返回 `UNSUPPORTED_PROJECT`，需先扩展映射。
- 未覆盖：跨机 SSH 转发联调、真实项目接入、并发多任务（单线程串行）。

验证命令与实际证据：

```sh
python3 run_e11e12.py test
python3 run_e11e12.py prepare
python3 run_e11e12.py run --request data/integration-sample/e11-a.json --out work/e11-a-01
python3 run_e11e12.py run --request data/integration-sample/e11-b.json --out work/e11-b-02
python3 run_e11e12.py run --request data/integration-sample/e12.json  --out work/e12-01
```

证据：`work/e11-a-01/result.json`、`work/e11-b-02/result.json`、`work/e12-01/result.json`、`work/api-client/`。
