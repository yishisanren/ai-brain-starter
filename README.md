# ai-brain-starter

让每个 AI 都带着你的大脑工作：一套给 Claude Code、Codex、Hermes 共用的记忆库模板、技能和定时任务，装好后每天自己记、自己汇总。

- **大脑**：`brain-template/` 是多个 agent 共用的记忆库，各 agent 只往自己的 inbox 写，汇总后沉淀为项目状态、经验、偏好。
- **分身**：`brain-load` + `goal-alignment`，新会话开工先读大脑，再给你一份开工简报，你回「确认」它才动手。
- **进化**：每天 19:00 日结，`brain-note` 读当天会话写回 inbox；凌晨 2 点 `brain-merge` 汇总进项目状态、经验、偏好，每周一写周总结，每月 1 日写月度归纳；汇总没按时跑，开工时会提醒。

## 一段话装好

把下面这段话发给你的 Claude Code 或 Codex，它会自己装好：

> 帮我安装 github.com/yishisanren/ai-brain-starter：按 docs/install.md 装好大脑、技能、指令块和定时任务，大脑放在 ~/brain，装完自检后告诉我怎么开工。

只想要开工简报：

> 帮我从 github.com/yishisanren/ai-brain-starter 只装开工简报：按 docs/install.md「只装开工简报」一节装好，告诉我怎么用。

几台电脑共用一份大脑，把「~/brain」换成 iCloud 之类会同步的文件夹。

接通三个 AI 共用插件（装全套的已经包含这一步）：

> 帮我按 github.com/yishisanren/ai-brain-starter 的 docs/share-skills.md，把各个 AI 接通成共用技能：已装的搬进大脑，以后装的默认共用。

接通之后，技能都放在大脑的 `skills/` 里，Claude Code、Codex、Hermes 都能用。以后装新技能照常跟 AI 说，默认三个 AI 共用，规矩见 `brain-template/skills/README.md`。

## 手动安装

四步安装（细节见 [docs/install.md](docs/install.md)）：

1. 复制 `brain-template/` 到你放记忆库的地方，把那个目录写进 `~/.config/brain/root`，本机名写进 `~/.config/brain/machine`。
2. 把 `skills/` 下五个目录放进大脑的 `skills/`，各个 AI 原来装的技能也搬进去（见 [docs/share-skills.md](docs/share-skills.md)），运行 `brain_materialize.py` 同步给所有 AI。
3. 把 `prompts/instruction-block.md` 贴进 `~/.claude/CLAUDE.md` 或 `~/.codex/AGENTS.md`，改占位符。
4. 按 [prompts/schedules.md](prompts/schedules.md) 建定时任务：每个 AI 每天 19:00 日结；只选一处每天 02:00 日汇总、每周一周总结、每月 1 日月度归纳。新开会话说「开工」。

仓库内容：`skills/` 五个技能（brain-load、brain-note、brain-find、brain-merge、goal-alignment），`brain-template/` 空记忆库，`prompts/` 指令块、定时任务提示词、开工简报模板、条目格式、手动汇总提示词，`docs/` 安装、接通共用技能与验证记录。
只依赖 Python 3.9+ 标准库。MIT 协议。
