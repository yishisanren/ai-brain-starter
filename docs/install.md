# 安装

三步装完。需要 Python 3.9 以上和 git，不装任何第三方包。技能只装一份，Claude Code、Codex、Hermes 共用。

## 第 1 步：建大脑

```bash
git clone https://github.com/yishisanren/ai-brain-starter.git
cp -R ai-brain-starter/brain-template ~/brain
echo 'export BRAIN_ROOT="$HOME/brain"' >> ~/.zshrc
echo 'export BRAIN_MACHINE="work-mac"' >> ~/.zshrc
source ~/.zshrc
```

大脑放进 iCloud、Obsidian 库之类会同步的目录，多台机器就能共用。机器名用小写字母、数字、连字符，它会出现在 `inbox/<机器>/` 路径和每条记录的来源里。

桌面版 app 有时读不到 shell 变量，可以改用文件：把根目录路径写进 `~/.config/brain/root`，机器名写进 `~/.config/brain/machine`。或者在 `MAP.md`「机器」表填一行，「识别」列填 `hostname` 输出里独有的一段。Windows 在系统环境变量里设 `BRAIN_ROOT` 和 `BRAIN_MACHINE`，命令里的 `python3` 换成 `python`。

## 第 2 步：技能放进大脑，同步给所有 AI

```bash
mkdir -p "$BRAIN_ROOT/skills" ~/.claude/skills
cp -R ai-brain-starter/skills/* "$BRAIN_ROOT/skills/"
python3 -B "$BRAIN_ROOT/skills/brain-note/scripts/brain_materialize.py"
```

脚本把大脑 `skills/` 里的技能放进 `~/.agents/skills/`，并给 Claude Code 建软链接。Codex 原生读 `~/.agents/skills/`，不用再做什么。

用 Hermes 的，在 `~/.hermes/config.yaml` 里确认有这一段，没有就加上：

```yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

本机已有同名技能时脚本报 `SKIP`、不覆盖，把它们列出来交给用户决定。以后装新插件的做法见大脑里的 `skills/README.md`。

## 第 3 步：贴指令块

把 `prompts/instruction-block.md` 里的两段贴进 `~/.claude/CLAUDE.md`（Codex 是 `~/.codex/AGENTS.md`），把 `<BRAIN_ROOT>`、`<机器>`、`<agent>` 改成你的值。两个 AI 都用的，两个文件各贴一份。

新开一个会话，说「开工」。AI 会运行 brain-load 读大脑，用 goal-alignment 给你一份开工简报，你回「确认」它才动手。做完说「记一下状态」，这次的工作就进了 inbox；下次在任何一个 AI 里说「开工」都能接上。

## 自检

```bash
python3 -B ~/.agents/skills/brain-load/scripts/brain_load.py --project demo
```

输出以「# brain-load 材料」开头、没有报错，就装好了。完整的四步验证见 [verify.md](verify.md)。

## 之后

- 让大脑进化：每天或每周把 `prompts/manual-merge.md` 交给 AI，它把 inbox 条目折叠进各项目的 STATUS，brain-load 下次就能读到。
- 用 git 管理 brain 根目录，每次追加都有历史。
- 装新插件：对任何一个 AI 说「把 <技能地址> 装成几个 AI 共用」，它按大脑里 `skills/README.md` 的规矩装。
- 换一台电脑：大脑同步过去后，跑一次第 2 步的同步命令，技能就全带过去了。
