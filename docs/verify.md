# 安装验证记录

在一个干净的临时目录按 [install.md](install.md) 走一遍：复制技能与 brain-template，设 `BRAIN_ROOT` 和 `BRAIN_MACHINE`，依次运行四个脚本。四步退出码均为 0。下面是原始输出，临时目录以 `$TMP` 代替。

```
环境：macOS 27.2，Python 3.9.6，2026-10-22 17:34 CST

```

## 准备：按 docs/install.md 第 1、2 步

```
$ cp -R ai-brain-starter/skills/* $TMP/home/.claude/skills/
$ cp -R ai-brain-starter/brain-template $TMP/brain
$ export BRAIN_ROOT="$TMP/brain" BRAIN_MACHINE="test-mac"

```

## 第 1 步：brain_load.py

```
$ python3 -B $TMP/home/.claude/skills/brain-load/scripts/brain_load.py --cwd "$TMP" --project demo
# brain-load 材料
根目录：$TMP/brain｜本机：test-mac｜今天：2026-10-22
项目：demo（依据：用户点名（新项目））

## STATUS.md
（尚无 STATUS.md：该项目还没有汇总过）

## 已确认偏好
（无）

## 最近两天 inbox 条目（0 条；STATUS generated=无）

## DECISIONS 最后 5 行
（无）

## 到期待回填的假设
（无）

## 待裁定（本项目）
（无）

## 本项目产物（artifacts/INDEX.md 最近 5 条；找回用 brain-find）
（无）
退出码：0

```

## 第 2 步：brain_write.py --dry-run 写一条示例条目

```
$ cat $TMP/entry.md
## 2026-10-22 17:34 · 手动 | 项目：demo（新）· 安装测试项目 | 来源：test-mac/claude-code | 会话：abcd1234
- 做了：按 docs/install.md 在干净目录装好技能和 brain-template
- 下一步：用 brain_store.py 存一个测试文件再用 brain_find.py 找回
- 来源等级：做了为工具实测
$ python3 -B $TMP/home/.claude/skills/brain-note/scripts/brain_write.py --agent claude-code --file $TMP/entry.md --dry-run
{"status": "dry-run", "path": "$TMP/brain/inbox/test-mac/claude-code/2026-10-22.md", "entries": 1, "warnings": []}
退出码：0

```

## 第 3 步：brain_store.py 存一个测试文件

```
$ echo "hello brain" > $TMP/hello.txt
$ python3 -B $TMP/home/.claude/skills/brain-note/scripts/brain_store.py --agent claude-code --project demo --title "安装测试文件" --session abcd1234 $TMP/hello.txt
{"status": "ok", "project": "demo", "ids": ["A-2026-10-22-01"], "stored": [{"id": "A-2026-10-22-01", "kind": "文件", "pointer": "artifacts/demo/2026-10-22-安装测试文件.txt", "abs_path": "$TMP/brain/artifacts/demo/2026-10-22-安装测试文件.txt", "md5": "df15bb1401a41e77a9506a1c46dd4eaa", "size": 12, "date": "2026-10-22"}], "duplicates": [], "index": "$TMP/brain/artifacts/INDEX.md", "entry_header": "## 2026-10-22 17:34 · 手动 | 项目：demo（新）· 安装测试文件 | 来源：test-mac/claude-code | 会话：abcd1234", "entry_lines": ["- 产物：[文件] 安装测试文件 | artifacts/demo/2026-10-22-安装测试文件.txt | md5 df15bb1401a4 · 12B | 原位置 test-mac:$TMP/hello.txt（A-2026-10-22-01；brain_store 复制并回读 md5 核实）"], "inbox": {"status": "ok", "path": "$TMP/brain/inbox/test-mac/claude-code/2026-10-22.md", "warnings": []}, "warnings": ["项目「demo」尚未登记，会按新项目写入；确认不是已有项目的别名再去掉 --dry-run"]}
退出码：0

```

## 第 4 步：brain_find.py 找回

```
$ python3 -B $TMP/home/.claude/skills/brain-find/scripts/brain_find.py --q "安装测试文件"
{"query": "安装测试文件", "project": "", "index": "$TMP/brain/artifacts/INDEX.md", "total_rows": 1, "hits": [{"id": "A-2026-10-22-01", "date": "2026-10-22", "project": "demo", "title": "安装测试文件", "kind": "文件", "pointer": "artifacts/demo/2026-10-22-安装测试文件.txt", "check": "md5 df15bb1401a4 · 12B", "origin": "test-mac:$TMP/hello.txt", "source": "test-mac/claude-code", "note": "—", "score": 17.0, "abs_path": "$TMP/brain/artifacts/demo/2026-10-22-安装测试文件.txt", "size": 12, "verify": "ok"}]}
| id | 产出日期 | 项目 | 标题 | 类型 | 本机路径 / URL | 核实 |
|---|---|---|---|---|---|---|
| A-2026-10-22-01 | 2026-10-22 | demo | 安装测试文件 | 文件 | $TMP/brain/artifacts/demo/2026-10-22-安装测试文件.txt | ok |
退出码：0

```

## 测试写了什么

与 brain-template 对比，临时 brain 只多了三处，都是第 3 步 brain_store.py 写的：

```
Files brain-template/artifacts/INDEX.md and $TMP/brain/artifacts/INDEX.md differ
Only in $TMP/brain/artifacts: demo
Only in $TMP/brain/inbox: test-mac
```

artifacts/INDEX.md 新增的一行：

```
| A-2026-10-22-01 | 2026-10-22 | demo | 安装测试文件 | 文件 | artifacts/demo/2026-10-22-安装测试文件.txt | md5 df15bb1401a4 · 12B | test-mac:$TMP/hello.txt | test-mac/claude-code | — |
```

inbox 条目原文：

```
# inbox · test-mac/claude-code · 2026-10-22

## 2026-10-22 17:34 · 手动 | 项目：demo（新）· 安装测试文件 | 来源：test-mac/claude-code | 会话：abcd1234
- 产物：[文件] 安装测试文件 | artifacts/demo/2026-10-22-安装测试文件.txt | md5 df15bb1401a4 · 12B | 原位置 test-mac:$TMP/hello.txt（A-2026-10-22-01；brain_store 复制并回读 md5 核实）
- 来源等级：产物为工具实测（brain_store 复制、md5 回读）
```

第 2 步用 `--dry-run`，只校验不写入，所以 inbox 里只有第 3 步自动追加的那一条。`BRAIN_ROOT` 指向临时目录，脚本没有碰机器上原有的记忆库。

## 共用插件：同步给所有 AI

2026-10-27 在临时目录按 [install.md](install.md) 第 2 步测试。测试时把脚本的家目录指到临时目录，结果如下：

| 场景 | 输出 | 退出码 |
|---|---|---|
| 首次同步四个技能 | 4 条 `UPDATE`，4 条 `LINK claude`；`~/.agents/skills` 有 4 个技能，`~/.claude/skills` 4 个软链接指向它们 | 0 |
| 大脑 `skills/` 里新放一个技能再同步 | `UPDATE hello-shared`、`LINK claude hello-shared` | 0 |
| 再跑一次 | `brain skills: no change（5 个已是最新）` | 0 |
| 直接改了 `~/.agents/skills` 下的副本 | `DRIFT hello-shared … 未覆盖` | 5 |
| 撤销改动，从大脑删掉这个技能 | `REMOVE hello-shared`，软链接一起删 | 0 |
| 本机已有同名、不是大脑装的技能 | `SKIP my-own … 未覆盖` | 0 |
| 按 [share-skills.md](share-skills.md) 第 3 步：`~/.claude/skills` 里原来的技能复制进大脑，原文件夹移到备份后同步 | `UPDATE my-own`、`LINK claude my-own` | 0 |
| 复制进大脑，但 `~/.claude/skills` 里的原文件夹没移走 | 只有 `UPDATE keep-old`，没有 `LINK claude`，Claude Code 仍读旧的那份 | 0 |
| 把这个原文件夹移到备份后再同步 | `LINK claude keep-old` | 0 |
| 同一个技能在 Claude Code 和 Codex 里各装一份、内容相同：只放一份进大脑，两份原文件夹都移到备份 | `UPDATE dup-same`、`LINK claude dup-same`；备份里两份都在 | 0 |
| 同名但两份内容不同，选了 Codex 那份放进大脑，两份原文件夹都移到备份 | `UPDATE dup-diff`、`LINK claude dup-diff`；共用目录里是 Codex 那份，备份里两份都在 | 0 |

## 全新电脑：从安装到换 AI 接着干

2026-10-27 模拟一台新 Mac：自带的 Python 3.9.6，家目录换成临时目录，环境里没有 `BRAIN_ROOT`、`BRAIN_MACHINE`。按 [install.md](install.md) 原样执行，每段命令单独开一个 shell（AI 执行命令就是这样）。大脑分别放在 `~/brain` 和带空格的 iCloud 路径 `~/Library/Mobile Documents/com~apple~CloudDocs/obsidian/4-助理/brain`，两遍结果相同：

| 场景 | 结果 |
|---|---|
| 第 1、2 步建大脑、同步技能 | 5 条 `UPDATE`，5 条 `LINK claude` |
| 自检（去掉环境变量跑，模拟桌面 app） | 输出大脑目录和机器名 `work-mac` |
| Claude Code「记一下状态」，项目 iot-weekly | 写入 `inbox/work-mac/claude-code/` |
| Codex 只说「开工」，当前目录没有映射 | 「最近有记录的项目」第一行是 iot-weekly，AI 据此加 `--project` 重跑 |
| 加 `--project iot-weekly` | 读到 Claude Code 写的「下一步：修周环比公式」 |
| 这条记录是 3 天前写的，还没汇总 | 仍然读得到，「开工」也仍然接到 iot-weekly |
| 项目已有 STATUS（昨天生成） | 只读昨天以后的条目，汇总过的不重复 |
| 记录是 20 天前写的，没汇总 | 读不到，要靠日汇总折进 STATUS |
| 指令块第 8 条的同步命令，填入带空格的路径 | 正常运行 |

## 自动运行：日结、汇总、开工提醒

2026-10-27 同样的新 Mac 模拟（Python 3.9.6、临时家目录、大脑放在带空格的 iCloud 路径），按 [schedules.md](../prompts/schedules.md) 里定时任务的命令逐条执行：

| 场景 | 结果 |
|---|---|
| 刚装完自检 | 「自动运行提醒」一行：日汇总还没有运行记录 |
| 当天在 Claude Code 里做了一段周报工作，另有一场汇总任务的会话 | 日结的会话摘要读到周报会话，跳过汇总任务自己的会话 |
| 日结按任务写法写入（先 `--dry-run`，再 `--consume`） | 写进 `inbox/work-mac/claude-code/`，暂存文件删掉 |
| 21:00 再跑一次日结 | 时间窗从 19:00 那次之后开始，会话 0 个，不重复写 |
| Hermes 写一行「无项目工作」 | 写入成功 |
| 产物行没写 brain_verify 核实 | 拒收，退出码 2 |
| 02:00 汇总的预处理 | 摘要落盘，列出 2 个文件 2 条条目、涉及 1 个项目 |
| 今天日汇总已跑 | 看门狗无问题 |
| 日汇总 20 天没跑、上周没有周总结、Claude Code 4 天没日结 | 三条都列出，并写明在哪里补跑；开工材料最前面显示同样的提醒 |

## 日汇总：让 AI 照提示词真跑一遍

2026-10-27 在同样的沙盒大脑里（新 Mac 模拟，大脑在带空格的 iCloud 路径），Claude Code、Codex、Hermes 各写一条当天日结，内容覆盖做了、决定、假设、下一步、阻塞、更正、经验、偏好。然后开一个全新的 AI 会话，拿 [schedules.md](../prompts/schedules.md)「日汇总」提示词执行：占位符换成沙盒路径，命令前加沙盒包装，其余一字不改。约 5 分钟跑完，最终回复第一行是「日汇总 2026-10-27 · 处理 3 个文件 3 条 · 涉及项目 sales-dashboard、weekly-report · 新建项目 sales-dashboard、weekly-report · 失败项 无」。

| 检查 | 结果 |
|---|---|
| 两个新项目的 STATUS | 都生成，首行 `---`、顶格，35 行；目标、现状、下一步、阻塞都按条目写进去，frontmatter 带 `generated` |
| `projects/INDEX.md` | 两个项目各一行；Hermes 的「无项目工作」没有当成项目 |
| 决定 | weekly-report 的 DECISIONS 记了「周报只发页面链接不发截图」 |
| 假设 | sales-dashboard 的 HYPOTHESES 记了 H-2026-10-27-01，带验证方法和到期日 |
| 更正 | `lessons/CORRECTIONS.md` 记了 B-2026-10-27-01，带根因 |
| 经验 | `lessons/LESSONS.md` 记了 L-2026-10-27-01，`lessons/INDEX.md` 登记了它 |
| 偏好「以后周报只要链接，别发截图」 | 范围是单个项目，且和同一条里的决定相同，按规则记进 weekly-report 的 DECISIONS，没有进 PREFERENCES |
| `_meta/runs/2026-10-27.md` | 记了处理的文件、条目数、新建项目、编号分配、偏好分流、回读结果 |
| `_meta/processed.json` | 登记 3 个 inbox 文件，sha256 和文件一致 |
| inbox 原文 | 没有改动 |
| 再跑一次预处理 | 0 条新条目，不会重复汇总 |
| 开工读 weekly-report | 读到 STATUS，当天条目标为「STATUS 生成前已有」；不再提醒日汇总没跑 |

这次运行查出模板两处和规则不一致，已修：大脑模板的 `lessons/CORRECTIONS.md` 改成规则用的 8 列表头（id、日期、项目、场景、偏差、根因、修正、来源）；`templates.md` 的 HYPOTHESES 加上「来源」列。
