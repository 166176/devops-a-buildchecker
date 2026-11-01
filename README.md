# BuildChecker 服务（E4 环境 + E5–E7 MVP）

本目录是共用仓库 `devops4/devops` 里 **A 组**的服务环境；仓库根目录是 B 组的 DRAFT 环境。
**下面所有命令都在本目录（`E4-A/`）里执行**，在仓库根目录执行 `make all` 构建的是 B 组的 draft。

E4 用 `make all` 建立可重复环境；E5–E7 用 `scripts/lab_cloud.py` 采集证据、运行检测和门禁。

## 第一次使用

```sh
mkdir -p ~/<学号> && cd ~/<学号>
git clone https://git.nju.edu.cn/devops4/devops.git && cd devops/E4-A
git config --local user.name  "<学号>"        # 统一用学号；服务器账号是共用的，不要加 --global
git config --local user.email "<学号>@localhost"  # E4 不推送，填本地示例值即可
make all
```

`git remote -v` 应指向真正的本组远程仓库。课堂试跑所用的 `/root/E4实验包/A-buildchecker` 只是本地模板；从它克隆不会自动同步到课程平台。共享服务器上的学号目录与 Git 身份只隔离个人工作和标记未来的提交，运行 `make all` 本身不会产生 Git 提交。

## 命令

| 命令 | 作用 | 证据（work/<时间>/） |
| --- | --- | --- |
| `make doctor` | 服务器与 Git 身份自检 | env.json |
| `make build` | 构建服务镜像 | build.log、image.json、toolchain.lock |
| `make test` | 容器内运行单元测试 | test.log |
| `make smoke` | 用 E3 样例做冒烟测试 | smoke.json |
| `make scan` | 密钥检查（工作区、Git 历史、镜像） | secret-scan.txt |
| `make all` | 以上五步 | 同一个证据目录 |
| `make shell` | 进入服务容器；仓库的 `work/` 挂到容器的 `/app/work`，在那里保存的文件退出后仍保留 | — |
| `make lock` | 修改 requirements-dev.in 后重新生成锁文件 | requirements-dev.lock |

预期：`make test` 全部通过；`make smoke` 输出 `"passed": true`，strace 记录中能看到 `config.h` 被打开，`app_output` 为 `1`；`make scan` 显示"未发现问题"。

## E5–E7 入口（lab_cloud.py）

`services/buildchecker/buildchecker/fullcheck.py` 实现全量检测；`scripts/lab_cloud.py` 是统一入口，只能在 Linux（WSL 或云主机）运行，证据固定写入本目录 `work/`。每次重跑换一个新的 `--out` 目录。

| 阶段 | 命令 | 关键结果 |
| --- | --- | --- |
| 构建 | `python3 scripts/lab_cloud.py build --out work/build-01` | 服务测试 15 项通过，生成 `course1020-buildchecker:local` |
| E5 | `python3 scripts/lab_cloud.py e5 --out work/e5-01` | `evidence/program-output.txt` 为 `1`；`make-db.txt` 声明 `main.o: main.c unused.h`；trace 中有 `config.h` 读取 |
| E6 | `python3 scripts/lab_cloud.py e6 --out work/e6-before` | 退出码 1，`findings.json` 有 MISSING(config.h) 与 REDUNDANT(unused.h) |
| E6 修复复检 | `python3 scripts/lab_cloud.py e6 --fixed --out work/e6-after` | 退出码 0，`findings=[]`；只有 Makefile 哈希变化 |
| 比对 | `python3 scripts/verify_e6_evidence.py --before work/e6-before/evidence/findings.json --after work/e6-after/evidence/findings.json` | `passed: true`，`changed_inputs: ["Makefile"]` |
| E7 判定测试 | `python3 -m unittest discover -s tests/e7 -v` | 6 项通过 |
| E7 门禁 | `python3 scripts/lab_cloud.py gate --out work/e7-01` | 八项 `passed=true`；`gate/gate-result.json`、`gate/results.csv` |

E7 的 CI workflow 是 `.github/workflows/e7-quality-gate.yml`，要求仓库根目录就是本环境（`services/buildchecker`、`tests/e7` 位于根）。执行步骤见 `docs/CI执行清单.md`。

## 约定

- 基础镜像按 digest 固定，升级时只改 `services/buildchecker/Dockerfile` 的 `ARG BASE_IMAGE` 一行，并在提交说明中写明新 digest。
- 新增 Python 依赖：写进 `requirements-dev.in`，执行 `make lock`，两个文件一起提交。
- 密钥只放在 `.env`（权限 600），不提交、不进镜像、不打印到日志。
- E4 每名组员各自在学号目录运行一次 `make all`，记录成功的 `work/<时间>/` 和所测源码 SHA，再与另一名组员对照。`work/` 默认不提交；E4 不要求个人创建分支、提交或合并。后续课程若要求提交原始证据，另按当时要求处理。
- 构建期软件源：默认使用 `deb.debian.org` 与 `pypi.org`，本地 WSL 和 GitHub Actions 可直接构建。本组 ECS 直连官方源很慢时，用 `--build-arg APT_MIRROR=mirrors.cloud.aliyuncs.com --build-arg PIP_INDEX=https://mirrors.aliyun.com/pypi/simple` 覆盖，不必改代码；内网镜像在本机不可达，故不作为默认值。
