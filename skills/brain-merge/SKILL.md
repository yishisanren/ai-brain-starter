---
name: brain-merge
description: 汇总公共记忆库 brain 的 inbox 条目，维护项目 STATUS、决策、假设、经验、偏差档案、偏好与索引；生成周总结、月度归纳与季度附加；执行修剪、Skill 发布与回退；处理用户裁定。只由 brain 的汇总定时任务（日汇总、周总结、月度归纳）或用户明确的「发布/回退/修剪/裁定」指令调用。
---

# brain-merge

根目录由脚本 `scripts/brain_common.py` 的 `find_root()` 定位（`~/.config/brain/root`）。脚本在 `~/.agents/skills/brain-merge/scripts/`。

## 模式

| 模式 | 触发 | 详细规则 |
|---|---|---|
| 日汇总 | 每天 02:00 定时任务；先运行 `brain_merge_prep.py --out auto`，再读它落盘的摘要 | references/daily.md |
| 周总结 | 每周一 12:30 定时任务 | references/weekly.md |
| 月度归纳（含季度附加） | 每月 1 日 12:30 定时任务 | references/monthly.md |
| 修剪执行 | 用户回复「修剪 全部」或编号 | references/monthly.md 修剪执行节 |
| Skill 草案、发布、回退、停用 | 日汇总附带；用户说「发布/回退/停用 <name>」 | references/skills-lifecycle.md |
| 裁定回写 | 用户在定时任务会话里或 `_meta/PENDING.md` 回复 D 项 | references/notify.md |

文件模板：references/templates.md。

## 写者边界

- 你是 `projects/`、`lessons/`、`user/`、`skills/`、`_meta/` 的唯一写者。汇总只在一台电脑的一个 AI 上跑。
- `inbox/` 只读，唯一例外是把疑似密钥条目的脱敏版追加到 `inbox/_sensitive/`。
- `MAP.md` 只在用户确认后改。
- 写文件：先写临时文件再改名；写完回读。

## 硬规则

1. 不删除任何条目或文件；只标记状态、移到 history 或 _archive。
2. 不编造日期、commit、路径、数字；条目里没有的就不写。
3. 矛盾不按时间先后自动裁决；保留双方、注明来源，登记待裁定。
4. 经验的真假由结果证明，不由出现次数证明；次数只决定是否起草 Skill。
5. 偏好只收以后都适用的话（分档见 references/daily.md）：带信号词的用户原话直接进「已确认」，不再问用户；一次性指令不收，单项目的要求写成该项目决定；agent 推断出来的偏好才需要用户确认。两者与已有偏好冲突时都登记待裁定。
6. 常规成功一句话带过，只有需要用户处理或异常时才展开（references/notify.md）。
7. 已发布 Skill 的内容只在用户说「发布」「回退」「停用」后改动。
