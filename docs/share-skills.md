# 接通共用技能

接通一次，Claude Code、Codex、Hermes 就共用一套技能：大脑的 `skills/` 是唯一的源，同步到本机 `~/.agents/skills/`，三个 AI 都从这里读。接通之后，以后装任何技能都默认三个 AI 共用，不用再交代。

把这段话发给任意一个 AI：

> 帮我按 github.com/yishisanren/ai-brain-starter 的 docs/share-skills.md，把各个 AI 接通成共用技能：已装的搬进大脑，以后装的默认共用。

按 [install.md](install.md) 装全套的，第 2 步就是在做这件事。

## 第 1 步：准备大脑的 skills 目录

还没有大脑的，先按 install.md 第 1 步建好。然后把本仓库的技能放进大脑，同步脚本在 brain-note 里：

```bash
mkdir -p "$BRAIN_ROOT/skills" ~/.claude/skills
cp -R ai-brain-starter/skills/* "$BRAIN_ROOT/skills/"
```

用 Hermes 的，在 `~/.hermes/config.yaml` 里确认有这一段，没有就加上：

```yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

Codex 原生读 `~/.agents/skills/`，不用改。

## 第 2 步：已装的技能搬进大脑

一个技能是一个带 `SKILL.md` 的文件夹。到下面几个目录里找：

| AI | 目录 | 不搬 |
|---|---|---|
| Claude Code | `~/.claude/skills/` | 软链接（已经是共用的） |
| Codex | `~/.codex/skills/` | `.system` |
| Hermes | `~/.hermes/skills/`，可能在分类子目录里 | `.bundled_manifest` 里列的 Hermes 自带技能；点开头的目录 |
| 共用目录 | `~/.agents/skills/` | 大脑同步过来的 |

插件市场装的插件（Claude Code 的 `~/.claude/plugins/` 等）不在这些目录里，不动。

1. 列出清单给用户看：名字、在哪几个 AI 里、几份内容是否相同。第三方技能先读 `SKILL.md` 和脚本，说清它会做什么。
2. 同名但内容不同的，列出来等用户选一份，不自己挑。
3. 选定的放进 `$BRAIN_ROOT/skills/<名称>/`，文件夹名和 `SKILL.md` 的 `name` 一致。
4. 原来的文件夹移到 `~/skills-backup-<日期>/<AI>/<名称>/`，不直接删。一定要移走：`~/.agents/skills/` 里留着同名的，同步会报 `SKIP`；`~/.claude/skills/` 里留着同名的，同步不报错，但 Claude Code 会一直用旧的那份。

## 第 3 步：同步

```bash
python3 -B "$BRAIN_ROOT/skills/brain-note/scripts/brain_materialize.py"
```

每个技能出一行 `UPDATE`，Claude Code 再出一行 `LINK claude`。缺 `LINK claude` 或者有 `SKIP` 的，对应目录里还有旧文件夹没移走，回到第 2 步。

## 第 4 步：指令块写上默认共用

`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md` 里要有这一条（装了全套的，[instruction-block.md](../prompts/instruction-block.md) 第 8 条已经有了）：

```
装任何技能（插件）都默认装成几个 AI 共用：按 <BRAIN_ROOT>/skills/README.md 放进 <BRAIN_ROOT>/skills/<名称>/，再运行 python3 -B <BRAIN_ROOT>/skills/brain-note/scripts/brain_materialize.py 同步给所有 AI。不要只装进某一个 AI 的私有目录，也不要直接改 ~/.agents/skills 下的副本。
```

## 之后

- 装新技能照常跟 AI 说「装一下 X」，它按这一条放进大脑再同步，三个 AI 新开会话就能用。
- 换一台电脑：大脑同步过去，跑一次第 3 步。
- 改技能、限定机器、删技能的规矩，见大脑里的 `skills/README.md`。
