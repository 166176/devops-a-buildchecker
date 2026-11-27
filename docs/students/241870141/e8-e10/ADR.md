# 决策记录（A 轨 EChecker 教学实现）

## 背景与约束

- 受测项目是受限 C/Make 样例：两个翻译单元（main.o、helper.o）、项目内头文件、显式规则与简单变量。
- E8 要求“历史图可复用”，E9 要求“逐提交更新并报告新增/消除”，E10 要求“增量与全量在完整集合上一致”。
- 环境只有 gcc/make/git/strace，无网络；不能调用外部模型或下载额外工具。
- 复用必须保守：宁可多刷新，也不能漏边。

## 选择与替代方案

**选择 1：用配置签名（key）判定复用，而不是按文件 mtime 或 Git diff。**

- 签名 = 各 `.c/.h` 的预处理指令行 + Makefile 中以 TAB 开头的配方行 + `CFLAGS` + `gcc --version` 首行。
- 备选 A：按 `git diff --name-only` 判断受影响的 `.c`。缺点：头文件内的 `#include` 变化不会让 `main.c` 变“被修改”，会漏掉失效（StudentE9A 用例正是锁这一点）。
- 备选 B：按 mtime。缺点：`git checkout` 与容器挂载会改写 mtime，结果不可重复。
- 代价：`#define` 值变化、注释变化也会触发刷新（保守，偏慢）。这在教学样例可接受。

**选择 2：实际依赖用 `gcc -MM` 重算，而不是复用 BuildChecker 的 strace 轨迹。**

- E8 的历史图来自真实 BuildChecker（strace + `make -p`），并断言与 `gcc -MM` 在对象目标上的投影一致；此后每次增量扫描用 `gcc -MM`（快、可重复、无需 ptrace）。
- 代价：`gcc -MM` 只看到预处理器层面的包含关系，看不到链接期输入；因此只比较对象目标，不与 `app` 链接目标混比。

**选择 3：刷新粒度取“全部目标”，而不是按目标精确失效。**

- 复用命中即整目标复用，任一 key 变化即刷新全部对象目标。
- 代价：`helper.o` 在只有 `main.c` 变化时也会刷新；E10 的 include/flags/header 三类显示增量与全量耗时基本持平（比值 0.93/0.96/1.03）。
- 收益：不会漏边；30 行矩阵作为“不漏边”的对照网。

**选择 4：声明图每次重算，发现差集每次重算。**

- 即使 `actual` 完全复用，`declared` 与 `findings` 也按当前提交重算。
- 原因：E9 C3 只改 Makefile，`actual` 复用而两项 MD 必须消除；若连 findings 一起复用就会得出错误结论（StudentE8A 用例锁定）。

## 代价与覆盖范围

- 覆盖：普通函数体变化、新增 include（源文件或头文件内）、仅声明变化、CFLAGS 变化、无变化。
- 不覆盖：隐式规则/模式规则、`|` order-only 依赖、多目标规则、非 GNU Make 构建、链接期依赖、文件删除后的增量语义。
- 已知偏差：`#define` 数值变化会触发保守刷新；`scan()` 计时含 Git 调用与 `gcc -MM`，不含完整 clean build。

## 验证命令与实际证据

```sh
# 三个阶段（本人 OUT）
python3 -m unittest discover -s labs/e8e10 -p test_profile.py -v      # Ran 11 tests, OK
# E8：真实 BuildChecker 基线与复用
work/e8-A-manual.0Iq8X8/{baseline.json,incremental.json,buildchecker/}
# E9：C0→C3 逐提交
work/e9-A-manual.xf8cZw/{baseline,C1,C2,C3}.json
# E10：六类×5 次
work/e10-A-manual.s1etZU/matrix/{results.csv,performance-summary.csv,gate.json}
```

结论：`gate.json` 为 `passed=true, rows=30`；最终 BuildChecker 重检与 `gcc -MM` 投影一致，只剩 `REDUNDANT main.o unused.h`。
