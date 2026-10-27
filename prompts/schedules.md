# 定时任务：让大脑自己跑起来

装完技能和指令块后建这些任务，大脑就每天自己记、自己汇总，不用再手动说「记一下状态」。

## 建哪些

| 任务 | 时间 | 建在哪 | 做什么 |
|---|---|---|---|
| brain 日结 | 每天 19:00（Claude Code 另加 21:00 补录） | 每台电脑上用的每个 AI 各建一个 | 读当天的会话记录，按项目写进 inbox |
| brain 日汇总 | 每天 02:00 | 所有电脑里只建一处 | 把 inbox 折叠进项目 STATUS、决策、假设、经验、偏好，重建索引，登记待裁定 |
| brain 周总结 | 每周一 12:30 | 和日汇总同一处 | 写上一周的「给你的一页」：进展、反复出现的问题、停滞的项目、待裁定 |
| brain 月度归纳 | 每月 1 日 12:30 | 和日汇总同一处 | 写上个月的归纳和修剪建议；1、4、7、10 月加季度附加 |

汇总三个任务建在哪：大脑 `_meta/runs/` 里已经有 `.md` 运行记录，说明别的电脑或别的 AI 已经在汇总，这里只建日结。没有，就建在这台电脑最常开着的 AI 上，优先 Claude Code 桌面版。两处同时汇总会把台账写乱。

## 先换占位符

下面的提示词和配置里，占位符一律换成绝对路径，定时任务里不要用 `~`：

- `<HOME>`：`echo $HOME` 的结果
- `<BRAIN_ROOT>`：`cat ~/.config/brain/root` 的结果
- `<机器>`：`cat ~/.config/brain/machine` 的结果

再建好日结要用的暂存目录：`mkdir -p ~/.local/state/brain/claude-daily`。

## Claude Code（桌面版）

1. 用定时任务工具 `create_scheduled_task` 建，`cronExpression` 用本地时间：

   | taskId | title | cronExpression | 提示词 |
   |---|---|---|---|
   | brain-daily-note | brain 日结 | `0 19,21 * * *` | 下文「日结 · Claude Code」 |
   | brain-merge-daily | brain 日汇总 | `0 2 * * *` | 下文「日汇总」 |
   | brain-merge-weekly | brain 周总结 | `30 12 * * 1` | 下文「周总结」 |
   | brain-merge-monthly | brain 月度归纳 | `30 12 1 * *` | 下文「月度归纳」 |

2. 免确认：定时任务跑到命令时如果弹权限确认，会一直停在那里。把下面几条追加进 `~/.claude/settings.json` 的 `permissions.allow`（文件里已有的内容保留，只追加；`<BRAIN_ROOT>` 等换成绝对路径后，前面再加一个 `/`，例如 `Edit(//Users/me/brain/**)`）：

   ```json
   "Bash(python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_digest.py:*)",
   "Bash(python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_verify.py:*)",
   "Bash(python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_write.py:*)",
   "Bash(python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_materialize.py)",
   "Bash(python3 -B <HOME>/.agents/skills/brain-merge/scripts/brain_merge_prep.py:*)",
   "Bash(date:*)",
   "Read(/<HOME>/.agents/skills/**)",
   "Read(/<BRAIN_ROOT>/**)",
   "Edit(/<BRAIN_ROOT>/**)",
   "Read(/<HOME>/.local/state/brain/**)",
   "Edit(/<HOME>/.local/state/brain/**)"
   ```

3. 建好后对每个任务点一次「立即运行」（或用 `run_scheduled_task`），看会话里没有停在权限确认上：日结最后输出条目和 brain_write 的 JSON，日汇总第一行是「日汇总 <日期>」。停住了就在确认框选「始终允许」，再跑一次。
4. 定时任务只在 Claude 桌面 app 开着时运行；到点时 app 没开或电脑睡着，下次打开时补跑。命令行版 Claude Code 没有本地定时任务，用同一台电脑上的桌面版建。

## Codex（app）

1. 在 Codex 的「自动化」里建日结：每天 19:00，本地运行，工作文件夹选大脑文件夹 `<BRAIN_ROOT>`，提示词用下文「日结 · Codex」。你能直接建自动化就建；不能，就把名称、时间、文件夹、提示词原样告诉用户，请用户在自动化页面新建。
2. Codex 默认只能写当前工作文件夹。在 `~/.codex/config.toml` 加上下面这段（已有 `[sandbox_workspace_write]` 就只往 `writable_roots` 里追加），平时在别的文件夹里说「记一下状态」也能写进大脑：

   ```toml
   [sandbox_workspace_write]
   writable_roots = ["<BRAIN_ROOT>", "<HOME>/.local/state/brain"]
   ```

3. 这台电脑没有 Claude Code、要让 Codex 汇总：日汇总、周总结、月度归纳也照上表的时间建成自动化，工作文件夹同样选大脑文件夹。
4. 建好后对日结点一次「立即运行」，确认最后输出了条目和 brain_write 的 JSON。

## Hermes

日结由脚本完成，不需要提示词。Hermes 的 `--script` 只认 `~/.hermes/scripts/` 下的文件，先放一个转调用的包装：

```bash
mkdir -p ~/.hermes/scripts
cat > ~/.hermes/scripts/brain_hermes_daily.py <<'EOF'
#!/usr/bin/env python3
"""cron 包装：转调 brain-note 技能里的 Hermes 日结脚本。"""
import os, pwd, runpy, sys
sys.dont_write_bytecode = True
runpy.run_path(os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".agents/skills/brain-note/scripts/brain_hermes_daily.py"), run_name="__main__")
EOF
hermes cron create "0 19 * * *" --name "brain 日结" --script brain_hermes_daily.py --no-agent --deliver local
```

脚本会给 default 和每个专职 profile 各写一条日结。先跑一次 `python3 -B ~/.agents/skills/brain-note/scripts/brain_hermes_daily.py --dry-run` 看输出。

## 提示词

每段提示词的第一行标记（`#brain-daily-run`、`#brain-merge`）要保留：日结读会话记录时靠它跳过大脑自己的任务会话。

### 日结 · Claude Code

```
#brain-daily-run
你是 <机器> 上的 Claude Code，执行 brain 日结。本任务每天 19:00 和 21:00 各触发一次，每次都是增量：只处理上次日结之后的新内容，有新内容就补录，没有就不写。只做下面这些事，不修改 brain 下任何其他文件。所有命令必须逐字使用下面的写法，不要加 cd、管道、heredoc、&& 或重定向，否则会触发权限确认、任务会卡住。

1. 运行：python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_digest.py --agent claude-code --since auto
2. 看输出第二行「时间窗：<起点> → <终点>」和第三行「会话：N 个」。时间窗从上次日结开始，摘要里只有这段时间的新内容。
   - N > 0：继续后面的步骤，只为这些新内容写条目，不重复上次日结已写过的事。同一项目今天已有条目也照写，汇总会把多条折叠。
   - N = 0 且起点日期不是今天：今天还没有任何日结，只写一行「## T · 日结 | 无项目工作 | 来源：<机器>/claude-code」，然后做第 6、7 步。
   - N = 0 且起点日期是今天：今天已经日结过、之后没有新内容，直接回复「无新内容」并结束，不写任何条目。
3. 运行：date '+%Y-%m-%d %H:%M'，得到当前时间 T；再把 T 去掉「-」「:」和空格，得到文件名时间戳 S（例如 202609141903）。
4. 用读文件工具读 <HOME>/.agents/skills/brain-note/references/entry-format.md，按其中格式为摘要里的每个项目写一条类型「日结」的条目，标题时间用 T，来源写 <机器>/claude-code。
   - 项目 id：先对照摘要末尾的「已有项目」清单，同一件事复用已有 id；会话里用户说过的项目名优先（别名按清单换成正式 id）；否则用摘要里的「映射项目」；都对不上才按内容总结一个小写字母、数字、连字符的 id，写成「项目：<id>（新）· <一句话>」。
   - 维度缺就省略；每条正文不超过 25 行；结论标来源等级（工具实测／用户告知／推断）。
   - 写任何「产物：[文件]」行之前，必须先运行：python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_verify.py <路径1> <路径2>，按输出写「（未入库；brain_verify 核实 <大小> <修改时间>）」。不能用会话记录、ls 或「摘要列出」代替；没跑 brain_verify 的产物不写。brain_write 会拒收不合格的产物行。
   - 不抄录密钥、token、密码、带凭证的链接。
5. 用写文件工具把全部条目写入新文件：<HOME>/.local/state/brain/claude-daily/entries-S.md
6. 先运行：python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_write.py --agent claude-code --file <HOME>/.local/state/brain/claude-daily/entries-S.md --dry-run
   返回 JSON 的 warnings 里有「相似」「别名」「不必标（新）」提示：按提示改用已有项目 id，写到新文件名 entries-S-1.md，后面的命令都改用这个文件名。
   再运行：python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_write.py --agent claude-code --file <HOME>/.local/state/brain/claude-daily/entries-S.md --consume
   退出码 2：按返回的 detail 修正，写到新文件名 entries-S-2.md 后，按同样写法再运行一次；退出码 3：删掉疑似密钥的行后同样重试一次。
7. 运行：python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_materialize.py
8. 最终回复：写入的条目原文、brain_write 返回的 JSON、同步输出。
```

### 日结 · Codex

```
#brain-daily-run
你是 <机器> 上的 Codex，执行 brain 日结。只做下面这些事，不修改 brain 下任何其他文件：
1. 读 <HOME>/.agents/skills/brain-note/SKILL.md 和 <HOME>/.agents/skills/brain-note/references/entry-format.md。
2. 运行：python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_digest.py --agent codex --since auto
3. 按「日结模式」为摘要里的每个项目写一条类型「日结」的条目，来源写 <机器>/codex，标题时间用 date '+%Y-%m-%d %H:%M' 的结果。项目 id：先对照摘要末尾的「已有项目」清单，同一件事复用已有 id；会话里用户说过的项目名优先（别名换成正式 id）；否则用摘要的「映射项目」；都对不上才按内容总结一个小写字母、数字、连字符的 id，写成「项目：<id>（新）· <一句话>」。维度缺就省略；每条正文不超过 25 行；结论标来源等级。写任何「产物：[文件]」行之前，必须先运行：python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_verify.py <路径1> <路径2>，按输出写「（未入库；brain_verify 核实 <大小> <修改时间>）」；没跑 brain_verify 的产物不写。摘要显示没有会话、且今天还没日结过，只写一行「## <时间> · 日结 | 无项目工作 | 来源：<机器>/codex」；今天已日结过、没有新内容，回复「无新内容」并结束。
4. 先用 heredoc 把全部条目交给：python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_write.py --agent codex --dry-run；返回 warnings 里有「相似」「别名」「不必标（新）」提示就改用已有 id 重写条目。然后去掉 --dry-run 正式写入。
   退出码 2：按返回的 detail 修正后重试一次；退出码 3：删掉疑似密钥的行后重试一次。
5. 最终回复：写入的条目原文和 brain_write 返回的 JSON。
```

### 日汇总

```
#brain-merge
你是 <机器> 上的 AI，执行 brain 公共记忆库的日汇总。规则全文在 <HOME>/.agents/skills/brain-merge/ 下：先完整读 SKILL.md、references/daily.md、references/templates.md、references/notify.md，再开始。只写 brain 根目录下的 projects/、lessons/、user/、_meta/ 和 inbox/_sensitive/；inbox 其他文件、artifacts/、MAP.md、skills/ 一律不改。brain 根目录：<BRAIN_ROOT>

步骤：
1. 运行：python3 -B <HOME>/.agents/skills/brain-merge/scripts/brain_merge_prep.py --out auto
   它把预处理摘要写到 <HOME>/.local/state/brain/merge-prep/<时间>.md（条目全文、文件清单与 sha256、涉及项目、编号台账、STATUS 格式问题），只打印路径和统计。读这个 .md。涉及项目的 STATUS / DECISIONS / HYPOTHESES / LESSONS 和全局文件（projects/INDEX.md、_meta/PENDING.md、_meta/processed.json、_meta/alerts.json、user/PREFERENCES.md、lessons/LESSONS.md、lessons/CORRECTIONS.md、lessons/INDEX.md、skills/REGISTRY.md）都直接读 brain 下的原文件。不要为读文件写辅助脚本，不要运行本提示词之外的任何命令。
2. 条目数为 0 且文件清单为空：在 _meta/runs/<今天>.md 写一行「无新条目」（文件已存在就追加一节），最终回复「日汇总 <日期>：无新条目」，结束。
3. 按 daily.md 第一步到第五步处理：预检、归类、按项目折叠（STATUS 整体重写不超 60 行，DECISIONS / HYPOTHESES / LESSONS / CORRECTIONS / PREFERENCES 按来源键查重追加，history 追加原文）、冲突判定（不自动裁决，登记 PENDING）、重建 projects/INDEX.md 与 lessons/INDEX.md、写 _meta/runs/<今天>.md（文件已存在就追加一节「## <时间> · 日汇总」，不覆盖已有内容）。每个文件写完回读。STATUS 首行必须是 ---，frontmatter 与标题一律顶格；摘要里 STATUS 格式问题列出的项目顺手修正。
4. 全部写入并回读成功后更新 _meta/processed.json：对摘要「文件」表里每个文件写 {"hash": <sha256>, "entries": <条目数>}，保留已有条目；任一写入失败则不更新 processed，在 runs 里记失败项。
5. 运行：python3 -B <HOME>/.agents/skills/brain-note/scripts/brain_materialize.py

交付：最终回复就是交付物，直接写在本会话里：
- 第一行：日汇总 <日期> · 处理 N 个文件 M 条 · 涉及项目 <id 列表> · 新建项目 <id 列表或无> · 失败项 <或无>
- 新增待裁定：每项按 notify.md 五段式（事项、对象是什么、判断、一句理由、可直接回复的短指令），项目 id 必须配一句不超 30 字的人话解释；没有就写「无待裁定」
- 记一行哪些 STATUS 被重写、哪些台账有追加
用户可能直接在本会话回复裁定（例如「D-… 合并 A→B」「D-… 不合并」「确认 P-…」）：按 notify.md 的「裁定回写」与「合并执行」做，改完回读并回复改了哪些文件。
硬规则：不编造日期、commit、路径、数字，条目里没有的不写；不删除任何条目或文件；不抄录密钥；矛盾不按时间先后裁决。所有命令逐字使用上面的写法，不加 cd、管道、heredoc、&& 或重定向。
```

### 周总结

```
#brain-merge
你是 <机器> 上的 AI，执行 brain 公共记忆库的周总结。先完整读 <HOME>/.agents/skills/brain-merge/SKILL.md 和 <HOME>/.agents/skills/brain-merge/references/weekly.md。brain 根目录：<BRAIN_ROOT>

1. 运行：date '+%Y-%m-%d %H:%M'，确认今天日期，算出上周一与上周日。复盘区间为上周一至周日。
2. 输出文件按覆盖周命名：<BRAIN_ROOT>/_meta/weekly/<上周一所在的 ISO 周 YYYY-Www>.md，不是生成日所在周。若该文件已存在，先读再决定是否重写，不覆盖别人手改的内容。
3. 按 weekly.md 读材料：上周的 _meta/runs/*、各活跃项目的 STATUS / DECISIONS / HYPOTHESES / LESSONS / history、lessons/CORRECTIONS.md、_meta/PENDING.md、skills/REGISTRY.md、上一份 _meta/weekly/*。
4. 按 weekly.md 的文件结构写「给你的一页」九节与「明细」，写完回读。活跃项目超过 8 个时第 1、4 节只列本周有日结条目的项目。
5. 只写这一个文件，不改 projects/ 等其他台账。

交付：最终回复第一行写文件路径，然后原样给出文件里「给你的一页」全文。
硬规则：每个「模式」「停滞」判断必须引用具体条目日期与来源；没有样本写「无」，不写 0% 或 100%；不编造数字。命令逐字使用上面的写法，不加 cd、管道、heredoc、&& 或重定向。
```

### 月度归纳

```
#brain-merge
你是 <机器> 上的 AI，执行 brain 公共记忆库的月度归纳。先完整读 <HOME>/.agents/skills/brain-merge/SKILL.md 和 <HOME>/.agents/skills/brain-merge/references/monthly.md。brain 根目录：<BRAIN_ROOT>

1. 运行：date '+%Y-%m-%d %H:%M'，确认今天日期；归纳区间为上个自然月。季度末后的那一次（1 月、4 月、7 月、10 月）按 monthly.md 加季度附加。
2. 输出文件：<BRAIN_ROOT>/_meta/monthly/<上月 YYYY-MM>.md。若已存在，先读再决定是否重写。
3. 按 monthly.md 读材料：上月全部 _meta/weekly/*、各项目全部长期文件、lessons/*、user/PREFERENCES.md、_meta/PENDING.md、_meta/runs/*、skills/REGISTRY.md、上一份 _meta/monthly/*。
4. 按 monthly.md 的文件结构写，写完回读。修剪清单只列出，不执行；用户回复「修剪 全部」或编号后再按 monthly.md 修剪执行节做。
5. 只写这一个文件，不改其他台账。

交付：最终回复第一行写文件路径，然后原样给出文件里「给你的一页」全文。
硬规则：没有样本写「无」；不编造数字；命令逐字使用上面的写法，不加 cd、管道、heredoc、&& 或重定向。
```
