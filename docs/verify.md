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
