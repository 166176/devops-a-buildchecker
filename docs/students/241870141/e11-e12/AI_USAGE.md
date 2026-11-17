# AI使用记录

- 工具/模型/日期：AI 编码助手（Copilot 会话内代理），2026-11-17。
- 输入上下文与问题：E11–E12 操作手册（公共准备、E11、E12、真实项目接入、GitHub 提交）、`labs/e11e12/{pipeline,prepare,server,test_contract}.py`、`run_e11e12.py`；问题是如何完成 A 轨 E11-A/E11-B/E12 全链路、补契约测试并提交。
- 模型建议：
  1. 按手册顺序执行 build → test → prepare → e11-a → e11-b → e12 → API 联调，保留 `work/` 证据；
  2. 新增 4 个契约测试（产物哈希/相对 URI、缺 schema、空白幂等键、重启后未完成任务）；
  3. 把 E11-B 的候选构建超时定位到 `deb.debian.org` 过慢，建议改用镜像站但保留原候选文件。
- 采纳/拒绝及理由：
  - 采纳 1、3：手册路线与网络适配直接对应验收项，且有原始日志可回查。
  - 采纳 2 并进一步修复实现：`test_blank_idempotency_key_is_rejected` 首跑失败，说明参考实现确有缺口；选择修 `server.py` 而不是把测试改成“空白键被接受”，因为接受空白键会让幂等语义失效。
  - 拒绝：曾考虑直接改 `pipeline.py`，让增量路径复用 `full_check` 的 `actual` 而不重算——会掩盖增量实现本身的错误，且与“增量/全量对照”的验收目的冲突。
- 人工修改：逐项核对每阶段 `commit` 是否等于 base/target、`artifact.sha256` 是否与文件一致、`X-Content-SHA256` 是否等于清单值；把报告中的 job_id/trace_id、镜像 ID、耗时与失败原因按实际输出填写；确认 `validation.checks` 五项均为 true、复检只剩 RD。
- 实际验证命令/输入/结果：
  - `python3 run_e11e12.py test` → `Ran 14 tests ... OK`；
  - `e11-a` → SUCCEEDED（full-check + incremental-check，added `MISSING main.o extra.h`）；
  - `e11-b` → SUCCEEDED（iter-01 MISSING_MAKE，iter-02 build=0，运行输出 1，validation accepted）；
  - `e12` → SUCCEEDED（draft/full-check/incremental-check/repair/recheck）；
  - API：提交→轮询→下载，幂等同 job_id，冲突 409，空白键 400，重启后已完成任务可查。
- 贡献边界：`pipeline.py`、`prepare.py`、`run_e11e12.py`、`test_contract.py` 与 `vendor/draft` 为课程参考实现，本人未改算法；本人修改 `server.py` 一行键校验并新增 `test_contract_student.py`；报告、ADR 的数据均来自本次实际运行。
