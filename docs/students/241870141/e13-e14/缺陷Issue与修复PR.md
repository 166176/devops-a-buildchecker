# 缺陷 Issue 与修复 PR

**基线说明**：2026-11-27 起仓库主线切换为组长仓库 `KasuAri27/devops-e5-e7-a-241880370`（`5d9ee87`）。本文件记录的两个缺陷在新基线上的状态：缺陷 1 以重放形式保留（组长树仍未修），缺陷 2 由组长 `service.py` 的进程内实现取代。

## 缺陷 1：增量重建检查依赖墙钟单调（已关闭）

| 项目 | 内容 |
| --- | --- |
| Issue | https://github.com/166176/devops-a-buildchecker/issues/7 |
| 修复 PR | https://github.com/166176/devops-a-buildchecker/pull/8（合并 `c91ca07`，旧谱系） |
| 新基线重放 | 提交 `ebe6ff3`（`labs/e8e10/lab.py` + `test_profile.py`） |
| 影响面 | `labs/e8e10/lab.py` 的 `validate()`；E10 补丁验收、E11–E14 的 repair 阶段都经过它 |
| 严重级别 | 阻断（正确补丁被回滚，任务被判失败） |

现象（旧谱系留下的证据 `work/_pre-rebase/e14-sample-00-clockstep-failure/validation/`）：

```
accepted=false
checks={'patch_applies': True, 'build': True, 'test': True,
        'header_change': False, 'no_missing': True}
```

`config.h` mtime 早于 `main.o`/`app`，`incremental.log` 为 `make: 'app' is up to date.`——被改写的头文件比目标文件更“旧”。

根因：旧实现用 `time.sleep(1.05)` + 改写 `config.h` 制造 mtime 先后关系。宿主机时钟在此期间回退约 1.2s，改写后的头文件 mtime 落到目标文件之前，`make` 判定无需重建，`header_change` 失败，`validate()` 按设计回滚。

修复（重放到组长树，组长版本仍是 `time.sleep(1.05)`）：

```python
def edit_header_for_rebuild(sandbox):
    """Change the header and make sure make sees it even after a clock step."""
    (sandbox/'config.h').write_text('#define VALUE 2\n')
    newest=max(x.stat().st_mtime for x in sandbox.iterdir() if x.is_file())
    os.utime(sandbox/'config.h',(newest+1,newest+1))
```

回归：`labs/e8e10/test_profile.py::ProfileTests::test_header_edit_wins_after_backward_clock_step`。

红绿验证（镜像 `course-e11e12:241870141`，在新基线上执行）：

- 修复后整套 `labs/e8e10`：`Ran 12 tests ... OK`
- 临时改回 `time.sleep(1.05)`：新测试失败 `AssertionError: 1795772577.9062011 != 1795776176.8583806`
- 恢复后单测：`Ran 1 test ... OK`
- 新基线上重跑 E14 单容器固定样例：五阶段 SUCCEEDED（`job-abab0d6708194012a9280fb53e6ba6b3`）

## 缺陷 2：四服务容器无法读取宿主用户创建的仓库（已由基线解决）

| 项目 | 内容 |
| --- | --- |
| 旧谱系修复 | `2af7088`、`dac72c7`、`ca50ffb`（PR #6），做法是在 `compose.yaml` 注入 `GIT_CONFIG_*` |
| 新基线方案 | 组长 `labs/e13e14/service.py` 在进程内 `os.environ.setdefault('GIT_CONFIG_COUNT'/'KEY_0'/'VALUE_0')`，与 Compose 无关 |
| 现状 | 采用组长 `service.py` 与组长 `compose.yaml`（不含 `GIT_CONFIG` 环境块），本轮四容器运行全部正常 |

现象（旧谱系 CI）：`echecker HTTP 422 ... fatal: detected dubious ownership in repository at '/course/work/ci-e14/base-project'`。

根因：四个角色以 `user: "0:0"` 运行，而 `orchestrate.py` 以宿主用户创建工作目录，`git` 拒绝跨用户仓库。

新基线验证：`docker compose config` 通过；四容器 `healthy` 后样例、H1、恢复三次运行都由四个角色各自处理同一 job（`work/e14-compose-*/services.log`），无 `dubious ownership` 报错。

## 远端 CI（新基线）

切换基线后无法用 PR 合并（两个谱系无共同祖先），改为在 `e13e14-rebase` 分支与 `main` 上直接运行工作流：

| 工作流 | 分支 | 结论 |
| --- | --- | --- |
| E7 A quality gate | `e13e14-rebase` | 通过 |
| E8-E10 teaching validation | `e13e14-rebase` | 通过 |
| E11-E12 integration | `e13e14-rebase` | 通过 |
| E13-E14 integration gate | `e13e14-rebase` | 通过 |