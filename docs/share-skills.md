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

## 第 2 步：盘点本机的 agent

不要只看下面表里的目录。先把本机所有技能文件夹找出来（一个技能就是一个带 `SKILL.md` 的文件夹）：

```bash
find ~ -maxdepth 6 -name SKILL.md -not -path "*/node_modules/*" -not -path "*/.Trash/*" -not -path "$HOME/Library/*" 2>/dev/null
```

Windows 在 `%USERPROFILE%` 下搜同名文件。

按所在目录归到各个 agent，列给用户：agent、目录、技能个数。下面这些不是用户装的，列的时候标出来，不搬：

- 备份目录，名字里带 backup、restore 之类的。
- agent 自带的技能：Codex 的 `.system`；Hermes 技能目录里 `.bundled_manifest` 列的；Hermes 安装目录 `~/.hermes/hermes-agent/` 里的。
- 插件市场装的插件，比如 Claude Code 的 `~/.claude/plugins/`。
- 项目里的技能，比如某个仓库下的 `.claude/skills/`，只属于那个项目。

### 认识的 agent

| AI | 技能目录 | 怎么读共用目录 |
|---|---|---|
| Claude Code | `~/.claude/skills/` | 第 4 步同步时脚本建软链接 |
| Codex | `~/.codex/skills/` | 原生读 `~/.agents/skills/`，不用改 |
| Hermes | 每个 profile 一套，见下 | 每个 profile 的配置里加外部目录 |

### Hermes：每个 profile 逐个处理

Hermes 的每个 profile 有自己的技能目录和配置：

- 默认 profile：技能在 `~/.hermes/skills/`，可能在分类子目录里；配置是 `~/.hermes/config.yaml`。
- 其他 profile：技能在 `~/.hermes/profiles/<名字>/skills/`；配置是 `~/.hermes/profiles/<名字>/config.yaml`。
- 设了 `HERMES_HOME` 的，把上面的 `~/.hermes` 换成它。

每个 profile 的配置里都要有这一段，没有就加上：

```yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

每个 profile 的技能都按第 3 步搬。改了哪几个 profile 的配置，列给用户。

### 不认识的 agent

找到的技能文件夹不属于上面几个 agent 的，比如别的 AI 工具，或者另设了 `HOME`、`CODEX_HOME` 的一份 Codex：先不搬、不接，列出来问用户：在哪个目录、几个技能、有几个和别的 AI 同名，要不要接进来。

用户要接的，先查这个 agent 的文档：能加外部技能目录的，加上 `~/.agents/skills`，它的技能按第 3 步搬；不能加的，告诉用户只能给每个技能手动建软链接，以后新装的技能不会自动带过去，由用户决定。

## 第 3 步：已装的技能搬进大脑

只搬第 2 步里认识的 agent 和用户同意接的 agent。

1. 列出清单给用户看：名字、在哪几个 AI 里、几份内容是否相同。第三方技能先读 `SKILL.md` 和脚本，说清它会做什么。
2. 同名且内容相同的（整个文件夹逐个文件比对），只留一份放进大脑；同名但内容不同的，列出来等用户选一份，不自己挑。
3. 选定的放进 `$BRAIN_ROOT/skills/<名称>/`，文件夹名和 `SKILL.md` 的 `name` 一致。
4. 原来的文件夹移到 `~/skills-backup-<日期>/<AI>/<名称>/`，不直接删。一定要移走：`~/.agents/skills/` 里留着同名的，同步会报 `SKIP`；`~/.claude/skills/` 里留着同名的，同步不报错，但 Claude Code 会一直用旧的那份。

## 第 4 步：同步，再查一遍

```bash
python3 -B "$BRAIN_ROOT/skills/brain-note/scripts/brain_materialize.py"
```

每个技能出一行 `UPDATE`，Claude Code 再出一行 `LINK claude`。缺 `LINK claude` 或者有 `SKIP` 的，对应目录里还有旧文件夹没移走，回到第 3 步。

最后按第 2 步的盘点结果给用户一张表：每个 agent、每个 Hermes profile 是否已接通，没接的写原因。

## 第 5 步：指令块写上默认共用

`~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md` 里要有这一条（装了全套的，[instruction-block.md](../prompts/instruction-block.md) 第 8 条已经有了）：

```
装任何技能（插件）都默认装成几个 AI 共用：按 <BRAIN_ROOT>/skills/README.md 放进 <BRAIN_ROOT>/skills/<名称>/，再运行 python3 -B <BRAIN_ROOT>/skills/brain-note/scripts/brain_materialize.py 同步给所有 AI。不要只装进某一个 AI 的私有目录，也不要直接改 ~/.agents/skills 下的副本。
```

## 之后

- 装新技能照常跟 AI 说「装一下 X」，它按这一条放进大脑再同步，三个 AI 新开会话就能用。
- 换一台电脑：大脑同步过去，在那台电脑上按第 2 到 4 步再走一遍。
- 改技能、限定机器、删技能的规矩，见大脑里的 `skills/README.md`。
