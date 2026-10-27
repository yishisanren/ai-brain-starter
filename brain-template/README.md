---
title: brain 公共记忆库
---
# brain 公共记忆库

多个 AI agent 共用的一份记忆：各 agent 只往自己的收件箱写条目，汇总后沉淀为项目状态、经验和偏好。

| 路径 | 内容 | 谁写 |
|---|---|---|
| MAP.md | 机器识别、目录→项目、别名 | 你 |
| inbox/<机器>/<agent>/<日期>.md | 各 agent 每天的条目 | 该 agent，只经 brain-note 脚本 |
| projects/<项目>/ | STATUS、DECISIONS、HYPOTHESES | 汇总者 |
| lessons/ | 通用经验、偏差档案 | 汇总者 |
| user/PREFERENCES.md | 用户偏好 | 汇总者 |
| artifacts/ | 产物库与索引 INDEX.md | 各 agent，只经 brain-note 存档模式 |
| _meta/PENDING.md | 待你裁定的事项 | 汇总者 |
| _meta/runs/、weekly/、monthly/ | 每天的汇总记录、周总结、月度归纳 | 汇总者 |
| skills/ | 几个 AI 共用的插件（技能），规矩见 skills/README.md | 你，或按规矩装插件的 AI |

读：brain-load。写：brain-note（你说「记一下状态」，或每天 19:00 的日结定时任务）。找回产物：brain-find。汇总者是 brain-merge：一台电脑上的一个 AI 用定时任务每天 02:00 汇总，每周一 12:30 写周总结，每月 1 日 12:30 写月度归纳。
