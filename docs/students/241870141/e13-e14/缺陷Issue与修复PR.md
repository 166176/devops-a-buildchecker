# 缺陷 Issue 与修复 PR

判定提交 `457d088` 上 CI 全绿（run `44066345128`：`contracts`、`four-services`）。

## 缺陷 1：增量重建检查依赖墙钟单调（已关闭）

| 项目 | 内容 |
| --- | --- |
| Issue | https://github.com/166176/devops-a-buildchecker/issues/7 |
| 修复 PR | https://github.com/166176/devops-a-buildchecker/pull/8（合并 `c91ca07`） |
| 发现阶段 | E14 固定样例五阶段运行时偶发 `REPAIR_REJECTED` |
| 影响面 | `labs/e8e10/lab.py` 的 `validate()`；E10 补丁验收、E11–E14 的 repair 阶段都经过它 |
| 严重级别 | 阻断（正确补丁被回滚，任务被判失败） |

现象（`work/e14-sample-00-clockstep-failure/validation/`）：

```
accepted=false
checks={'patch_applies': True, 'build': True, 'test': True,
        'header_change': False, 'no_missing': True}
rollback=True
```

关键证据：`config.h` mtime `18:29:25.008`，`main.o` `18:29:25.110`，`app` `18:29:25.139`，`incremental.log` 为
`make: 'app' is up to date.`——被改写的头文件比目标文件更“旧”。

根因：旧实现用 `time.sleep(1.05)` + 改写 `config.h` 制造 mtime 先后关系。宿主机/WSL 时钟在此期间回退约 1.2s，
被改写的头文件 mtime 落到目标文件之前，`make` 判定无需重建，`header_change` 检查失败，`validate()` 按设计回滚。

修复：不再依赖时钟单调，改为把改写后的 `config.h` mtime 顶到沙箱内所有文件之上：

```python
def edit_header_for_rebuild(sandbox):
    (sandbox/'config.h').write_text('#define VALUE 2\n')
    newest=max(x.stat().st_mtime for x in sandbox.iterdir() if x.is_file())
    os.utime(sandbox/'config.h',(newest+1,newest+1))
```

回归：`labs/e8e10/test_profile.py::ProfileTests::test_header_edit_wins_after_backward_clock_step`。

红绿验证（在 `course-e11e12:241870141` 容器内执行）：

- 修复后：`Ran 12 tests ... OK`
- 临时改回 `time.sleep(1.05)`：新测试失败 `AssertionError: 1794911504.1038346 != 1794915103.0443187`
- 修复后重跑 `work/e14-sample-01`：五阶段 SUCCEEDED（`job-895daafd6e9944669fd23eb7bac14025`）

## 缺陷 2：四服务容器无法读取宿主用户创建的仓库（已关闭）

| 项目 | 内容 |
| --- | --- |
| 发现阶段 | E14 Compose 就绪后首次运行五阶段（CI `four-services` 作业） |
| 修复提交 | `2af7088`、`dac72c7`、`ca50ffb`（PR #6） |
| 严重级别 | 阻断（EChecker 阶段 422） |

现象：`echecker HTTP 422 ... COMMAND_FAILED ['git','rev-parse','HEAD'] fatal: detected dubious ownership in repository at '/course/work/ci-e14/base-project'`。

根因：四个角色以 `user: "0:0"` 运行，而 `orchestrate.py` 以宿主用户创建工作目录；`git` 拒绝跨用户仓库。
第一次修复把 `GIT_CONFIG_*` 放进 `x-common.environment`，但每个服务自己的 `environment:` 映射会整体替换锚点，
设置没有进入容器；第二次修复改为独立的 `x-common-env` 锚点并在每个角色里 `<<: *common-env` 合并。

验证：

- `docker compose config` 中四个服务都出现 `GIT_CONFIG_COUNT/KEY_0/VALUE_0`；
- 容器内对照实验（`work/_tmp/owner_test.sh`）：不带设置时 `git rev-parse HEAD` 报 dubious ownership，带设置时输出 `40c43299…`；
- CI 新运行中 `four-services` 通过（见 `候选发布说明.md` 的 CI 链接）。
