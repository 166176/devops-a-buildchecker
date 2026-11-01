# E7 CI 与合并门禁执行清单（A 轨，待执行）

本清单在 GitHub 授权可用后执行，目的是产出验收记录 C05、C06 所需的运行记录。**仓库根目录必须是本环境**（`services/buildchecker`、`tests/e7`、`.github/workflows` 位于根）。若从组仓库推送，请把 `E4-A/` 的内容作为独立仓库根，避免路径 `E4-A/...` 与 workflow 中的路径不匹配。

## 0. 前置条件

- GitHub 账号；免费个人账号需使用**公开**仓库才能配置分支保护。
- 在 WSL/云主机安装 `gh`，并确认 Docker 可用：

```sh
gh --version || (sudo apt-get update && sudo apt-get install -y gh)
docker version
```

## 1. 建仓库、首次推送与正常 CI

```sh
cd E4-A
git init -b main
git add .
git commit -m "E5-E7 A: detection gate, evidence entry and CI workflow"

gh auth login --hostname github.com --git-protocol https --web --scopes workflow
gh auth setup-git --hostname github.com

gh repo create devops-a-buildchecker --public --source . --remote origin --push
gh repo view --json nameWithOwner,visibility,url
```

等待并确认首次运行：

```sh
gh run list --limit 5
read -r -p "本次运行 ID: " run_id
gh run watch "$run_id" --exit-status
echo "CI_EXIT_CODE=$?"
mkdir -p work/ci-normal
gh run download "$run_id" --dir "work/ci-normal/artifacts-$run_id"
```

预期：`CI_EXIT_CODE=0`，日志中 `16 passed`、八项门禁全部通过；artifact `e7-a-evidence-*` 下载成功并含 `commit.txt`。

## 2. main 分支保护

先核对检查名与 App ID：

```sh
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
sha=$(git rev-parse HEAD)
gh api "repos/$repo/commits/$sha/check-runs" \
  --jq '.check_runs[] | {name, conclusion, app_id: .app.id, app_slug: .app.slug}'
```

预期：名称 `e7-a-quality-gate`，`app_slug` 为 `github-actions`。若 App ID 不是 `15368`，先修改 `ci/A-main-protection.json` 再执行：

```sh
mkdir -p work/ci-protection
gh api --method PUT "repos/$repo/branches/main/protection" \
  --input ci/A-main-protection.json \
  --jq '{checks: .required_status_checks.checks, strict: .required_status_checks.strict, enforce_admins: .enforce_admins.enabled}' \
  | tee work/ci-protection/protection-setup.json
gh api "repos/$repo/branches/main/protection" > work/ci-protection/protection.json
```

预期：输出包含 `e7-a-quality-gate`，`strict` 与 `enforce_admins` 均为 `true`。

## 3. 故意失败 PR 与合并拦截

```sh
git switch -c e7-gate-reject-demo
cp ci/rejection-demo/A/test_ci_reject_demo.py services/buildchecker/tests/
git add services/buildchecker/tests/test_ci_reject_demo.py
git commit -m "Demonstrate CI rejection with wrong test oracle"
git push -u origin e7-gate-reject-demo
gh pr create --base main --head e7-gate-reject-demo \
  --title "Demonstrate E7 merge rejection" \
  --body "故意写错 version 返回值预期，验证 CI 失败与禁止合并。"
read -r -p "PR 编号: " pr_num
gh pr checks "$pr_num" --watch
```

预期：测试 `1 failed / 16 passed`（`version` 期望 1、实际 0），检查失败。

```sh
mkdir -p work/ci-rejection
gh pr merge "$pr_num" --merge > work/ci-rejection/merge-rejection.log 2>&1
echo "MERGE_ATTEMPT_EXIT_CODE=$?"
gh pr view "$pr_num" --json state,mergeStateStatus,headRefOid,url > work/ci-rejection/PR.json
gh run list --branch e7-gate-reject-demo --event pull_request --limit 3
read -r -p "失败的 PR 运行 ID: " fail_run
gh run view "$fail_run" --log-failed > work/ci-rejection/failed-check.log
gh run download "$fail_run" --dir "work/ci-rejection/artifacts-$fail_run"
```

预期：`MERGE_ATTEMPT_EXIT_CODE=1`，`PR.json` 为 `OPEN` / `BLOCKED`，拒绝日志含 `base branch policy prohibits the merge`。

## 4. 修复预期、恢复通过并合并

```sh
cp ci/rejection-demo/A/fixed/test_ci_reject_demo.py services/buildchecker/tests/
git add services/buildchecker/tests/test_ci_reject_demo.py
git commit -m "Correct version success oracle"
git push
gh pr checks "$pr_num" --watch
gh pr view "$pr_num" --json state,mergeStateStatus,headRefOid,url
gh run list --branch e7-gate-reject-demo --event pull_request --limit 3
read -r -p "通过的 PR 运行 ID: " pass_run
mkdir -p work/ci-recovery
gh run download "$pass_run" --dir "work/ci-recovery/artifacts-$pass_run"
gh pr view "$pr_num" --json state,mergeStateStatus,headRefOid,url > work/ci-recovery/PR-before-merge.json
gh pr merge "$pr_num" --merge
gh pr view "$pr_num" --json state,mergedAt,mergeCommit,url > work/ci-recovery/PR-merged.json
```

预期：最新提交 `CLEAN`、`17 passed`（16 项服务测试 + 1 项门禁演示测试），PR 合并成功，`PR-merged.json` 含 `mergedAt` 与 `mergeCommit`。

## 5. 完成后回填

- 把 `work/ci-normal/`、`work/ci-protection/`、`work/ci-rejection/`、`work/ci-recovery/` 的结论填入 `docs/验收记录.csv` 的 C05、C06，并把状态改为 `PASS`。
- 在 `docs/实验报告.md` 的“CI 与合并门禁”一节补上 run id、artifact 路径与合并提交。

## 6. 本次实际执行记录（2026-11-02）

| 项目 | 实际值 |
| --- | --- |
| CI 仓库 | <https://github.com/166176/devops-a-buildchecker>（公开，根 = A 环境，`SOURCE.txt` 记录来源 SHA） |
| 正常运行 | run `41352638727`，`success`，41 秒，16 passed，八项门禁 passed |
| 分支保护 | `e7-a-quality-gate` / App 15368，`strict=true`，`enforce_admins=true`，审批 0 |
| 失败运行 | run `41352778461`，`1 failed / 16 passed`（`assert 0 == 1`） |
| 合并拦截 | PR #1 `OPEN/BLOCKED`，`gh pr merge` 退出码 1，日志含 `base branch policy prohibits the merge` |
| 恢复运行 | run `41352902075`，`success`，17 passed |
| 最终合并 | PR #1 `MERGED`，`mergedAt=2026-11-01T21:37:54Z`，`mergeCommit=79704a773c7007c7ae2b99fbff90e893cf521a8c` |
| 证据位置 | `E4-A/work/ci-normal/`、`ci-protection/`、`ci-rejection/`、`ci-recovery/` |

注：`gh` 通过设备码登录账号 `166176`；仓库公开以便免费账号启用分支保护。

## 7. 常见问题

| 现象 | 处理 |
| --- | --- |
| `gh` 无法打开浏览器 | 手动打开 https://github.com/login/device 输入设备码 |
| 分支保护 403 | 仓库需为公开（免费账号） |
| 分支保护 422 | 只保留 `checks`，核对检查名与 App ID |
| Actions 无运行记录 | 确认 workflow 已推送且仓库启用 Actions |
| 推送后仍是旧检查 | 核对 `headRefOid` 与最新提交，等待新运行 |
| workflow 报 action 版本不存在 | 将 `actions/checkout`、`upload-artifact` 改为当前可用版本 |
