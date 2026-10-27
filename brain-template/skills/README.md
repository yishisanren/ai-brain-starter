# 共用插件（技能）

这个目录放几个 AI 共用的技能。一个技能就是一个带 `SKILL.md` 的文件夹，文件夹名和 `SKILL.md` 开头的 `name` 一致。

## 怎么共用

```
大脑 skills/<名称>/            ← 唯一的源，跟大脑一起同步到每台电脑
   │  brain_materialize.py
   ▼
本机 ~/.agents/skills/<名称>/
   ├─ Codex：原生读取这个目录
   ├─ Claude Code：~/.claude/skills/<名称> 软链接过来（脚本自动建）
   └─ Hermes：~/.hermes/config.yaml 的 skills.external_dirs 里有 ~/.agents/skills
```

装一次，三个 AI 都能用；换一台电脑，跑一次同步就全带过去。

## 接通与装新技能

第一次用，先接通：各个 AI 原来装的技能搬进这里，见仓库的 `docs/share-skills.md`。

接通之后，装新技能照常跟任何一个 AI 说「装一下 X」。指令块第 8 条让它默认装成共用，按下面做：

1. 拿到技能文件夹，先读一遍 `SKILL.md` 和里面的脚本，告诉你它会做什么。
2. 确认文件夹名和 `SKILL.md` 的 `name` 一致，放进本目录 `<名称>/`。
3. 运行 `python3 -B <BRAIN_ROOT>/skills/brain-note/scripts/brain_materialize.py`。
4. 把脚本输出给你看。新开会话后各个 AI 都能用。

## 规矩

- 只改这里的源，不改 `~/.agents/skills` 下的副本。副本被改过，同步会拒绝覆盖并报 `DRIFT`。
- 本机已有同名技能、内容不同：脚本报 `SKIP`，不覆盖，列出来等你选。
- 只给某几台电脑用：在技能文件夹里放 `skill.lock.json`，写 `{"targets":{"machines":["work-mac"]}}`。
- 不要了：从这里删掉，再同步一次，各 AI 一起删。
- 第三方技能先看内容再装，带脚本的尤其要看。
