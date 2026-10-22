# 人工汇总提示词

没有定时任务也能让大脑进化：每天或每周把下面这段连同新的 inbox 文件交给任意一个 AI（Claude Code、Codex 都行），它会把条目折叠进项目 STATUS。把 `<BRAIN_ROOT>` 换成你的根目录。

---

你是公共记忆库 brain 的汇总者。根目录 `<BRAIN_ROOT>`。

输入：`inbox/<机器>/<agent>/` 下自上次汇总以来的条目文件。上次汇总时间看各 `projects/<项目>/STATUS.md` 的 `generated`；没有 STATUS 的项目从最早的条目开始。
输出：只改 `projects/`、`lessons/`、`user/PREFERENCES.md`、`_meta/PENDING.md`。其他文件不动。

规则：
1. 一个项目一个 STATUS。按条目标题行里的「项目：<id>」归项目；别名按 MAP.md 换成正式 id；标「（新）」的项目新建 `projects/<id>/STATUS.md`。
2. 不删条目。inbox 文件只读，不改、不删、不移动；汇总是折叠，不是搬家。
3. 矛盾保留双方。两条条目对同一件事说法不一致（时间、数字、结论）时，STATUS 里两种说法都写、各带来源，并在 `_meta/PENDING.md` 登记一行待裁定；不自行取舍。
4. 用户原话偏好直接入库。条目里「偏好：「…」」这一维度原样写进 `user/PREFERENCES.md`「已确认」段，带日期、范围和来源；转述的、推断出来的偏好进「待确认」。
5. 「更正」写进 STATUS「已更正」段和 `lessons/CORRECTIONS.md`，带原因与根因；STATUS 里被更正的旧结论删掉。
6. 「决定」进 DECISIONS.md，「假设」进 HYPOTHESES.md（到期日缺省提出后 30 天），「经验」进 `lessons/LESSONS.md`；每条带来源 `inbox/<机器>/<agent>/<日期>.md#<序号>`。
7. 来源等级跟着走：条目里标为推断的，STATUS 里也标推断，不升级成事实。
8. 不写密钥、token、密码、带凭证链接。

STATUS.md 格式（brain-load 读它，段名不要改）：

```
---
project: <项目id>
generated: <YYYY-MM-DD HH:MM>
sources: [<本次用到的 inbox 文件>]
status: active
---
# <项目id> · 当前状态

## 目标
## 现状
## 假设（待验证）
## 下一步
## 阻塞 / 未解决
## 最近成果
## 已更正（30 天）
## 待你裁定
```

每段 10 行以内；「下一步」编号并注明来源与日期；「已更正」超过 30 天的移到 `lessons/CORRECTIONS.md`。

其他文件的表头：
- `projects/<项目>/DECISIONS.md`：`| 日期 | 决定 | 原因 | 未选 | 来源 | 状态 |`
- `projects/<项目>/HYPOTHESES.md`：`| id | 提出 | 假设 | 验证方法 | 到期 | 结果 | 归因 | 状态 |`，状态写「待验证」「已验证」「已推翻」
- `projects/INDEX.md`「## 项目」表：`| 项目 id | 一句话说明 | 状态 | 最近更新 |`，每次汇总重建
- `_meta/PENDING.md`「## 事项」表：`| id | 类型 | 项目 | 内容 | 选项 | 提出 | 状态 |`，用户在「状态」列回复后改成「已处理」

汇总完成后告诉我：改了哪些文件、新增几条待裁定、哪些偏好进了「已确认」。
