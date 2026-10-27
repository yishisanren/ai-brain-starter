# ai-brain-starter

让每个 AI 都带着你的大脑工作：一套给 Claude Code 和 Codex 共用的记忆库模板与技能。

- **大脑**：`brain-template/` 是多个 agent 共用的记忆库，各 agent 只往自己的 inbox 写，汇总后沉淀为项目状态、经验、偏好。
- **分身**：`brain-load` + `goal-alignment`，新会话开工先读大脑，再给你一份开工简报，你回「确认」它才动手。
- **进化**：`brain-note` 把每次工作写回 inbox，`prompts/manual-merge.md` 把条目折叠进项目 STATUS，大脑越用越准。

## 一段话装好

把下面这段话发给你的 Claude Code 或 Codex，它会自己装好：

> 帮我安装 github.com/yishisanren/ai-brain-starter：按 docs/install.md 装好技能、大脑和指令块，大脑放在 ~/brain，装完自检后告诉我怎么开工。

只想要开工简报：

> 帮我从 github.com/yishisanren/ai-brain-starter 只装 skills/goal-alignment 这一个技能，装好后告诉我怎么用。

几台电脑共用一份大脑，把「~/brain」换成 iCloud 之类会同步的文件夹。

接通三个 AI 共用插件（装全套的已经包含这一步）：

> 帮我按 github.com/yishisanren/ai-brain-starter 的 docs/share-skills.md，把各个 AI 接通成共用技能：已装的搬进大脑，以后装的默认共用。

接通之后，技能都放在大脑的 `skills/` 里，Claude Code、Codex、Hermes 都能用。以后装新技能照常跟 AI 说，默认三个 AI 共用，规矩见 `brain-template/skills/README.md`。

## 手动安装

三步安装（细节见 [docs/install.md](docs/install.md)）：

1. 复制 `brain-template/` 到你放记忆库的地方，`export BRAIN_ROOT=<那个目录>`、`export BRAIN_MACHINE=<本机名>`。
2. 把 `skills/` 下四个目录放进大脑的 `skills/`，各个 AI 原来装的技能也搬进去（见 [docs/share-skills.md](docs/share-skills.md)），运行 `brain_materialize.py` 同步给所有 AI。
3. 把 `prompts/instruction-block.md` 贴进 `~/.claude/CLAUDE.md` 或 `~/.codex/AGENTS.md`，改占位符，新开会话说「开工」。

仓库内容：`skills/` 四个技能，`brain-template/` 空记忆库，`prompts/` 指令块、开工简报模板、条目格式、人工汇总提示词，`docs/` 安装、接通共用技能与验证记录。
只依赖 Python 3.9+ 标准库。MIT 协议。
