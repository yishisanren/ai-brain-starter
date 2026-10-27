# 手动汇总

想立刻汇总、某天汇总没跑，或者这台电脑没建定时任务：

- 建了汇总定时任务的：在那个 AI 的定时任务列表里，对「brain 日汇总」点立即运行。
- 没建的：把 [schedules.md](schedules.md) 里「日汇总」那段提示词换好占位符，直接发给 Claude Code 或 Codex。周总结、月度归纳同理。

手动和定时用的是同一份规则（brain-merge 技能），处理过的 inbox 文件记在 `_meta/processed.json`，重跑不会重复写。不要让两台电脑同时汇总。
