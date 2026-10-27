# 安装

四步装完：建大脑、接通共用技能、贴指令块、建定时任务。需要 Python 3.9 以上和 git，不装任何第三方包。技能只装一份，Claude Code、Codex、Hermes 共用。

新 Mac 第一次运行 `git` 或 `python3` 会弹窗要求安装「命令行开发者工具」。AI 看到这类报错时，请用户在弹窗里点「安装」，装完再继续。

## 第 1 步：建大脑

```bash
git clone https://github.com/yishisanren/ai-brain-starter.git
cp -R ai-brain-starter/brain-template ~/brain
mkdir -p ~/.config/brain
echo "$HOME/brain" > ~/.config/brain/root
echo "work-mac" > ~/.config/brain/machine
```

大脑位置和机器名写进 `~/.config/brain/` 下这两个文件，Claude Code、Codex、Hermes 从终端还是桌面 app 启动都读得到。只写成 `~/.zshrc` 里的环境变量不够：桌面 app 和 AI 执行命令用的 shell 多数不读 `.zshrc`。

大脑放进 iCloud、Obsidian 库之类会同步的目录，多台机器就能共用，上面两处 `~/brain` 换成那个目录。机器名用小写字母、数字、连字符，它会出现在 `inbox/<机器>/` 路径和每条记录的来源里。Windows 把这两个文件写在 `%USERPROFILE%\.config\brain\` 下，命令里的 `python3` 换成 `python`。

## 第 2 步：接通共用技能

技能放进大脑，同步给所有 AI，各个 AI 里原来装的技能也搬进来。细节见 [share-skills.md](share-skills.md)。

```bash
B="$(cat ~/.config/brain/root)"
mkdir -p "$B/skills" ~/.claude/skills
cp -R ai-brain-starter/skills/* "$B/skills/"
```

然后按 share-skills.md 第 2、3 步：先盘点本机的 agent，Hermes 每个 profile 逐个看，不认识的 agent 列出来问用户；再把原来装的技能搬进大脑：列清单，同名但内容不同的等用户选，原来的文件夹移到备份目录。搬完同步：

```bash
python3 -B "$(cat ~/.config/brain/root)/skills/brain-note/scripts/brain_materialize.py"
```

脚本把大脑 `skills/` 里的技能放进 `~/.agents/skills/`，并给 Claude Code 建软链接。Codex 原生读 `~/.agents/skills/`，不用再做什么。

用 Hermes 的，每个 profile 的配置（默认是 `~/.hermes/config.yaml`，其他在 `~/.hermes/profiles/<名字>/config.yaml`）里都要有这一段，没有就加上：

```yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

脚本报 `SKIP`，或者某个技能没有 `LINK claude`，说明对应目录里还有旧文件夹没移走，回到上面「搬进大脑」那一段处理。第 3 步贴的指令块里有一条「装技能默认共用」，接通之后，以后装任何技能都默认三个 AI 共用。

## 第 3 步：贴指令块

把 `prompts/instruction-block.md` 里的两段贴进 `~/.claude/CLAUDE.md`（Codex 是 `~/.codex/AGENTS.md`），把 `<BRAIN_ROOT>`、`<机器>`、`<agent>` 改成你的值。两个 AI 都用的，两个文件各贴一份。

## 第 4 步：建定时任务

按 [prompts/schedules.md](../prompts/schedules.md) 建：每个 AI 每天 19:00 日结；所有电脑里只选一处，每天 02:00 日汇总、每周一 12:30 周总结、每月 1 日 12:30 月度归纳。那份文件里有三个 AI 各自的建法、免确认设置和完整提示词。建好后每个任务点一次「立即运行」，确认没有停在权限确认上。

## 自检

```bash
env -u BRAIN_ROOT -u BRAIN_MACHINE python3 -B ~/.agents/skills/brain-load/scripts/brain_load.py --project demo
```

故意去掉环境变量跑一遍，模拟桌面 app。输出以「# brain-load 材料」开头、第二行是你的大脑目录和机器名，就装好了。刚装完、汇总还没跑过时，「自动运行提醒」会有一行「日汇总：还没有运行记录」，第一次日汇总跑完就消失。完整的验证见 [verify.md](verify.md)。

## 开始用

新开一个会话，说「开工」。AI 会运行 brain-load 读大脑，用 goal-alignment 给你一份开工简报，你回「确认」它才动手。之后每天 19:00 日结自动把当天的工作写进 inbox，凌晨汇总进项目状态；换 AI 前想立刻接上，就说一句「记一下状态」。在任何一个 AI 里说「开工」，它接最近一条记录的项目，也可以说「开工 <项目名>」指定。

## 只装开工简报

不建大脑，只要开工简报：

1. 把 `skills/goal-alignment` 复制进 `~/.agents/skills/`（Codex 读这里）和 `~/.claude/skills/`（Claude Code 读这里）。
2. 把 `prompts/instruction-block.md` 的「全局话题开工门禁」一段贴进 `~/.claude/CLAUDE.md` 和 `~/.codex/AGENTS.md`，其中第二条换成：「每个新的实质执行话题，先使用 goal-alignment 技能，出一份简短开工简报。这是全局触发规则，不受 goal-alignment 默认触发措辞限制。」没有这一段，开工简报只在 AI 自己觉得需要时才出。
3. 新开会话，交代一件要做的事，AI 先给开工简报，你回「确认」它才动手。

## 之后

- 看汇总结果：日汇总、周总结、月度归纳的结果写在各自定时任务的会话里；有待你裁定的事，直接在那个会话里回复短指令（如「D-… 不合并」）。不看也不会漏：开工简报会列本项目的待裁定，汇总没按时跑也会提醒。
- 想立刻汇总、或某天汇总没跑：在汇总所在的 AI 里对「brain 日汇总」点立即运行；没建定时任务的电脑，把 `prompts/manual-merge.md` 交给任意一个 AI。
- 用 git 管理 brain 根目录，每次追加都有历史。
- 装新技能：照常跟 AI 说「装一下 X」，它按指令块第 8 条放进大脑再同步，三个 AI 都能用。
- 换一台电脑：大脑同步过去后，在那台电脑上做第 1 步的两个配置文件，再按 share-skills.md 第 2 到 4 步走一遍，技能就全带过去了，那台电脑上原来装的技能也一起搬进大脑；第 4 步只建日结，汇总已经在别处跑。
