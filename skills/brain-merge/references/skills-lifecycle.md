# Skill 生命周期

## 起草（日汇总附带）

条件：同一标签下同场景同做法的经验，出现次数 ≥3 且来自 ≥2 个不同日期，或被 ≥2 个不同 agent 记录。

在 `skills/_drafts/<name>/` 生成：

- `SKILL.md`：frontmatter 只有 `name`、`description`（写清触发条件与范围）；正文依次为适用场景、所需输入与工具、步骤（操作级动词）、验证、失败处理、不适用条件（至少 3 条）。
- `skill.lock.json`：`name`、`version: "0.1.0"`、`source_lessons`、`targets.machines`（默认所有机器）、`agents`、`platforms`（各平台 untested）、`side_effects`、`created`。
- 脚本只用 Python 3 标准库，运行方式 `python3 -B`。

登记待裁定 skill-draft，周总结第 7 节提醒。

## 发布与回退（只由用户触发）

| 用户说 | 动作 |
|---|---|
| 发布 <name> | 冒烟：SKILL.md frontmatter 完整、脚本 `python3 -B -m py_compile` 通过、`--help` 能运行。通过后 `_drafts/<name>` 移到 `skills/<name>`；已有旧版则旧版先复制到 `_archive/<name>/<旧版本>/`，版本号次版本 +1；更新 REGISTRY 一行。冒烟失败不发布，回复原因 |
| 回退 <name> | 当前版本复制到 `_archive/<name>/<当前版本>/`；`_archive` 中上一版复制回 `skills/<name>`；REGISTRY 标「已回退到 x.y.z」并写原因 |
| 停用 <name> | 移到 `_archive/<name>/<版本>-disabled/`；REGISTRY 标 disabled。各机物化脚本会删除本机副本 |
| <name> 在 <平台> 可用 / 不可用 | REGISTRY 对应平台列改 verified / failed |

各机在 19:00 日结时运行 `brain_materialize.py`，按 bundle hash 更新本机 `~/.agents/skills/`。

## 反馈

- 条目里的「skill 反馈：skill:<name>@<版本> 有效|部分有效|无效：原因」汇入 REGISTRY「最近反馈」列，保留最近 5 条。
- 同平台同版本连续 2 次「无效」：登记待裁定 skill-failed，建议回退或停用；不自动回退。
- agent 私有的技能创建与记忆只作为经验来源，不反向覆盖公共版本。
