---
name: brain-find
description: 从公共记忆库 brain 的产物库找回之前任一 agent 存的文件或链接，核实后按当前渠道发给用户。用户说「把之前存的 X 发我」「找一下之前那个 X」「上次保存的那个包在哪」「brain-find」时使用。只读，不写 brain。
---

# brain-find

产物库在 `brain/artifacts/`，索引是 `artifacts/INDEX.md`，由各 agent 经 brain-note 的存档模式写入。本技能只查、核实、交付。
脚本在本技能目录的 `scripts/` 下，下文写作 `<技能目录>`（装好后在 `~/.agents/skills/brain-find`，Claude Code 经软链接也能从 `~/.claude/skills/brain-find` 找到）。Windows 用 `python` 代替 `python3`。

## 步骤

1. 从用户的话里取关键词：去掉「之前」「那个」「发我」这类虚词，留下东西本身的名字、用途、项目、版本。用户点了项目名就加 `--project`，说了大概时间就加 `--since`。

   ```
   python3 -B <技能目录>/scripts/brain_find.py --q "<关键词>" [--project <id或别名>] [--since YYYY-MM-DD]
   ```

2. 按结果处理：
   - 唯一命中且 `verify=ok`：直接交付。
   - 多个候选：列不超过 3 个（id · 产出日期 · 标题 · 备注里的版本说明），让用户选，不猜。
   - 无命中：先 `--list --project <id>` 看该项目全部产物；还没有就如实说产物库里没有。mac 上可用 `mdfind -name <文件名>` 按文件名兜底，找到的只报路径，不自动入库。
   - `verify=missing`：索引有、本机没有。把入库机器、原位置、库内路径告诉用户，说明可能是同步尚未完成或文件在别的机器。
   - `verify=md5-mismatch`：库内文件被改过，交付前说明。

3. 交付方式按渠道：

   | 渠道 | 做法 |
   |---|---|
   | Claude Code | 用发文件工具把 `abs_path` 发给用户；链接类回标题 + URL |
   | Codex | 没有发文件通道：回绝对路径，mac 上再运行 `open -R "<abs_path>"` 在 Finder 里选中它 |
   | Hermes | 用所在聊天渠道的发文件能力把 `abs_path` 发到当前会话；不可用时回路径。链接类直接发 URL |

   交付时附一句：id、产出日期、来源 agent、备注里的版本说明。

## 禁止

- 改 INDEX.md 或库内文件；往 artifacts/ 拷东西（那是 brain-note 存档模式的事）。
- 发 `inbox/_sensitive` 下的内容。
- 把没找到说成找到，或把相似的另一个版本当成用户要的那个。
