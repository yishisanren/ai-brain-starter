# ai-brain-starter

让每个 AI 都带着你的大脑工作：一套给 Claude Code 和 Codex 共用的记忆库模板与技能。

- **大脑**：`brain-template/` 是多个 agent 共用的记忆库，各 agent 只往自己的 inbox 写，汇总后沉淀为项目状态、经验、偏好。
- **分身**：`brain-load` + `goal-alignment`，新会话开工先读大脑，再给你一份开工简报，你回「确认」它才动手。
- **进化**：`brain-note` 把每次工作写回 inbox，`prompts/manual-merge.md` 把条目折叠进项目 STATUS，大脑越用越准。

三步安装（细节见 [docs/install.md](docs/install.md)）：

1. 复制 `skills/` 下四个目录到 `~/.claude/skills/`（Codex 是 `~/.codex/skills/`）。
2. 复制 `brain-template/` 到你放记忆库的地方，`export BRAIN_ROOT=<那个目录>`、`export BRAIN_MACHINE=<本机名>`。
3. 把 `prompts/instruction-block.md` 贴进 `~/.claude/CLAUDE.md` 或 `~/.codex/AGENTS.md`，改占位符，新开会话说「开工」。

仓库内容：`skills/` 四个技能，`brain-template/` 空记忆库，`prompts/` 指令块、开工简报模板、条目格式、人工汇总提示词，`docs/` 安装与验证记录。
只依赖 Python 3.9+ 标准库。MIT 协议。
