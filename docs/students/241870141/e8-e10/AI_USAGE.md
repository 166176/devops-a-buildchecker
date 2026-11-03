# AI 使用记录

- 工具/模型/日期：AI 编码助手（Copilot 会话内的代理），2026-11-03。
- 输入上下文与问题：课程 E8–E10 A 轨操作手册、`labs/e8e10/lab.py`、`test_profile.py`、`08_个人测试编写示例.md`；问题是“如何在受限样例上完成 E8/E9/E10 并补充独立预期的测试”。
- 模型建议：
  1. 按手册逐步执行 E8/E9/E10（不跳步），保留 `steps/` 日志；
  2. 新增四个测试类，分别锁定“复用但重算 findings”“头文件内 include 失效”“间接 include 增量=全量”“删除声明只消 RD”。
- 采纳/拒绝及理由：
  - 采纳：执行路线与用例选择；理由是它们直接对应 `scan()` 的 `key`/`reused`/`refreshed`/`added`/`resolved` 语义，可回归。
  - 拒绝：曾建议把刷新粒度改为“仅刷新受影响目标”并直接改 `lab.py`。理由是本次验收只要求“增量与全量一致”，改核心逻辑会放大漏边风险且偏离参考实现；改为在 ADR 的“扩展计划”中记录。
- 人工修改：逐条核对断言与手册预期（如 `resolved` 只应含两项 MISSING、`findings` 只剩 RD），并按实际输出填写报告中的 SHA、OUT、计时中位数；对 `StudentOwnCase` 的预期由本人改写为“只剩 MD config.h 且 resolved 只含 RD”。
- 实际验证命令/输入/结果：
  - `python3 -m unittest discover -s labs/e8e10 -p test_profile.py -v` → `Ran 11 tests`、`OK`、退出 0；
  - E8 `BASELINE_PASS`/`BUILDCHECKER_BASELINE_PASS`/`REUSE_PASS`；E9 `C1_REUSE_PASS`/`C2_REFRESH_PASS`/`C3_RESOLVED_PASS`；E10 `MATRIX_PASS`（六类各 5 次）与 `DYNAMIC_CROSSCHECK_AND_MATRIX_PASS`。
- 贡献边界：`lab.py` 为课程参考实现，本人未修改；`test_profile.py` 新增的四个 `Student*` 类为本人实验补充；报告、ADR 的结论与数据均来自本人本次运行的证据目录。
