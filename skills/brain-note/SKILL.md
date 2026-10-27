---
name: brain-note
description: 把当前项目状态写成条目，追加到公共记忆库 brain 今天的 inbox 文件。用户说「记一下状态」「记笔记」「brain-note」「换 agent 前记一下」时用手动模式；用户说「存一下」「保存起来」「保存这些」时用存档模式，把交付物存进 brain/artifacts/ 并登记索引；定时任务要求「日结」时先用脚本读会话记录再写。只经脚本写 inbox/<本机>/<本agent>/ 和 artifacts/，不碰 brain 其他文件。
---

# brain-note

脚本在本技能目录的 `scripts/` 下，下文写作 `<技能目录>`（装好后在 `~/.agents/skills/brain-note`，Claude Code 经软链接也能从 `~/.claude/skills/brain-note` 找到）。Windows 用 `python` 代替 `python3`。
写条目前先读 `references/entry-format.md`。

## 手动模式（默认）

1. 为本次会话涉及的每个项目写一条，类型「手动」。材料来自当前对话：做了什么、决定、假设、下一步、阻塞、产物、用户的更正与偏好。
2. 产物先核实：运行 `python3 -B <技能目录>/scripts/brain_verify.py <项目目录或文件> ...`（只读，给出是否存在、git 分支与领先落后、未提交改动、最近提交）。把核实结果写进「产物」。
3. 写入，条目经标准输入交给脚本：

   ```
   python3 -B <技能目录>/scripts/brain_write.py --agent <claude-code|codex|hermes> <<'EOF'
   ## 2026-09-14 16:20 · 手动 | 项目：brain | 来源：<机器>/claude-code | 会话：abcd1234
   - 做了：……
   EOF
   ```

   `<机器>` 是本机机器名（`~/.config/brain/machine` 里写的名字），`--agent` 与来源里的 agent 必须一致。
4. 退出码：0 成功；2 格式或来源错误，按 detail 改后重试；3 含疑似密钥，删掉那几行再试；4 回读不一致，如实告诉用户。返回 JSON 的 `warnings` 里出现「相似」「别名」「不必标（新）」：说明项目 id 该复用已有的；正式写入前先加 `--dry-run` 跑一遍看这些提示，改好 id 再写，写入后再改会造成重复条目。
5. 成功后把追加的条目原样给用户看，并说写进了哪个文件。

## 存档模式（用户说「存一下」「保存起来」「保存这些」）

把交付物存进 `brain/artifacts/<项目>/`，登记 `artifacts/INDEX.md`，以后任一 agent 都能用 brain-find 按描述找回。

1. 定对象：用户指了哪个就存哪个；没指就是本轮刚产出、刚发给用户的文件。多个文件各存各的，一次命令可传多个路径但共用一个标题，标题不同就分开跑。代码在 GitHub 上的不存文件，用 `--link` 记仓库或 Release 链接；Figma、在线文档等云端内容用 `--link` 记 URL。
2. 定标题：一句人话，写清是什么、什么版本、给谁用，例如「去广告模块 · 放行版」。以后靠它找回，不要用文件名当标题。版本差异、与旧版的关系写进 `--note`。
3. 项目 id 按手动模式第 1 条的规则定，优先复用已有 id；找不到合适的再新建。
4. 先 `--dry-run` 看 warnings 与查重，再去掉 `--dry-run` 正式存：

   ```
   python3 -B <技能目录>/scripts/brain_store.py --agent <claude-code|codex|hermes> --project <id> --title "<标题>" [--note "<版本差异或用途>"] [--session <会话id前8位>] <路径> [<路径> ...]
   python3 -B <技能目录>/scripts/brain_store.py --agent <agent> --project <id> --title "<标题>" --link <URL>
   ```

   Hermes 用绝对路径，`--session` 写成 `<profile>:<会话id>`。目录会先打成 zip 再存。
5. 退出码：0 成功；2 参数或项目 id 错误，按 detail 改；3 含疑似密钥，清理后再存；4 复制或回读校验失败，如实告诉用户。`status=duplicate` 表示同内容已在库中，把已有 id 告诉用户即可，不重复存。
6. 脚本会自己追加一条 inbox「手动」条目，不用再单独写。成功后把 `entry_lines` 原样给用户看，并说 id 和库内绝对路径。

## 日结模式（定时任务说「日结」）

Claude Code 与 Codex：

定时任务里只用下面这些固定写法的命令，App 才能免确认放行；不要用 heredoc、cd、管道拼接。

1. 取摘要：`python3 -B ~/.agents/skills/brain-note/scripts/brain_digest.py --agent <claude-code|codex> --since auto`。时间窗从本 agent 上一次日结开始，没有则从昨天 19:00 开始。
2. 每次运行都是增量：时间窗从本 agent 上次日结开始，摘要里只有新内容。有会话就只为新内容写条目（同一项目当天已有条目也照写，汇总会折叠）；没有会话且今天还没有日结（起点不是今天）就写一行「无项目工作」；没有会话且今天已日结过（起点是今天）就什么都不写，回复「无新内容」。Claude Code 的 21:00 运行就是靠这条补录 19:00 之后的工作。
3. 按摘要里的「映射项目」和会话内容归项目，每个项目写一条类型「日结」的条目，覆盖时间窗内全部工作。已经有手动条目的项目也写日结。写任何「产物：[文件]」行之前，必须先运行 `python3 -B ~/.agents/skills/brain-note/scripts/brain_verify.py <路径1> <路径2>`，按输出写「（未入库；brain_verify 核实 <大小> <修改时间>）」；不能用会话记录、ls 或「摘要列出」代替。brain_write 会拒收没写 brain_verify 或路径不存在的 [文件] 行（退出码 2）。
4. 脚本报错：写一行「会话记录不可读：<原因>」，不编内容。
   摘要末尾若有「候选产物」：不自动入库。确认是交付物的，先用 brain_verify.py 核实，再在对应项目条目里写 `- 产物：[文件] <标题> | <机器>:<路径>（未入库；brain_verify 核实 <大小> <修改时间>）`，让用户以后能说「存一下」；不确定的不写。
5. 写入：Claude Code 用写文件工具把全部条目写到 `~/.local/state/brain/claude-daily/entries-<YYYYMMDD-HHMM>.md`（每次新文件名），先运行 `python3 -B ~/.agents/skills/brain-note/scripts/brain_write.py --agent claude-code --file <该文件> --dry-run` 看 warnings，有相似或别名提示就改用已有 id 重写文件，再去掉 `--dry-run` 加 `--consume` 正式写入。Codex 可以沿用手动模式第 3 步的写法，同样先 `--dry-run`。摘要末尾附有「已有项目」清单，归项目时先对照它。
6. Claude Code 再运行 `python3 -B ~/.agents/skills/brain-note/scripts/brain_materialize.py`。
7. 最终输出：写入的条目原文、brain_write 返回的 JSON、物化输出。

Hermes 的日结由 default profile 的 19:00 cron 以 `--script --no-agent` 运行 `brain_hermes_daily.py`：脚本导出各 profile 会话、让每个有会话的 profile（含 default）自己写条目、逐个校验后统一写入 inbox，空闲 profile 合成一行「无项目工作」，最后同步公共技能。profile 不能调用工具，产物行由脚本经 brain_write 用 brain_verify 实测，路径不存在的产物行自动删掉。不需要模型审批，也不需要 cron 提示词。

## 生成模式（Hermes 专职 profile，由调度脚本调用）

只输出条目，用单独一行的 `<<<BRAIN-ENTRIES` 和 `BRAIN-ENTRIES>>>` 包起来；不调用工具，不写文件。

## 禁止

- 写 inbox 与 artifacts 以外的任何文件；手工编辑 inbox 文件或 artifacts/INDEX.md；不经 brain_store.py 往 artifacts/ 拷文件。
- 编造 commit、路径、日期；把推断写成事实。
- 抄录会话里的密钥、token、密码、带凭证链接。
