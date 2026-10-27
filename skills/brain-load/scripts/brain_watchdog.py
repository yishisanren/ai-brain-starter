#!/usr/bin/env python3
"""brain_watchdog：检查 brain 的自动运行有没有掉链子。只读，不调模型。brain_load 开工时调用，也可单独运行。

检查：
1. 日汇总：今天 `_meta/runs/<今天>.md` 是否存在（03:00 之后才检查）。
2. 周总结：上一个完整周的周总结是否存在（周一 13:00 前看再上一周）；汇总那周还没开始跑的不查。
3. 月度归纳：上个月的 `_meta/monthly/<YYYY-MM>.md` 是否存在（每月 2 日起检查）；上个月还没开始汇总的不查。
4. inbox：本机每个 agent 最近一个 inbox 文件是否超过 2 天没更新。
5. STATUS：首行不是 `---` 或开头被缩进的项目。
6. 技能副本漂移：~/.agents/skills 下的公共技能副本与上次同步记录的 bundle hash 不一致。

用法：python3 -B brain_watchdog.py
退出码：0 正常；1 有问题（问题逐行打印）。
"""
import datetime
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_common as bc  # noqa: E402

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PERIOD_RE = re.compile(r"^period:\s*(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})", re.M)
RERUN = "。补跑：在汇总所在 AI 的定时任务列表里，对「%s」点立即运行"


def run_dates(root):
    d = root / "_meta" / "runs"
    return sorted(f.stem for f in d.glob("*.md") if DATE_RE.match(f.stem)) if d.is_dir() else []


def check_daily(root, now, runs, out):
    if now.hour < 3:
        return
    today = now.date().isoformat()
    if not runs:
        out.append("日汇总：还没有运行记录。汇总任务建好后每天 02:00 运行，没建的按仓库 prompts/schedules.md 建")
    elif runs[-1] != today:
        out.append("日汇总：今天没有运行记录，最近一次是 %s%s" % (runs[-1], RERUN % "brain 日汇总"))


def weekly_covered(root, monday):
    wdir = root / "_meta" / "weekly"
    if not wdir.is_dir():
        return False
    iso = monday.isocalendar()
    tag = "%d-W%02d" % (iso[0], iso[1])
    for f in wdir.glob("*.md"):
        if f.stem == tag:
            return True
        m = PERIOD_RE.search(bc.read_text(f))
        if m and m.group(1) == monday.isoformat():
            return True
    return False


def check_weekly(root, now, runs, out):
    this_monday = now.date() - datetime.timedelta(days=now.date().weekday())
    target = this_monday - datetime.timedelta(days=7)
    if now.date().weekday() == 0 and now.hour < 13:
        target -= datetime.timedelta(days=7)
    end = target + datetime.timedelta(days=6)
    if not runs or runs[0] > end.isoformat() or weekly_covered(root, target):
        return
    out.append("周总结：覆盖 %s 至 %s 的周总结不存在%s" % (target.isoformat(), end.isoformat(), RERUN % "brain 周总结"))


def check_monthly(root, now, runs, out):
    if now.day < 2:
        return
    first = now.date().replace(day=1)
    prev = (first - datetime.timedelta(days=1)).strftime("%Y-%m")
    if not runs or runs[0] >= first.isoformat() or (root / "_meta" / "monthly" / ("%s.md" % prev)).is_file():
        return
    out.append("月度归纳：%s 的 _meta/monthly/%s.md 不存在%s" % (prev, prev, RERUN % "brain 月度归纳"))


def check_inbox(root, machine, now, out):
    base = root / "inbox" / machine
    if not base.is_dir():
        return
    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name.startswith(("_", ".")):
            continue
        files = sorted(f.stem for f in d.glob("*.md") if DATE_RE.match(f.stem))
        if not files:
            continue
        gap = (now.date() - datetime.date.fromisoformat(files[-1])).days
        if gap > 2:
            out.append("inbox：%s 最近一个文件是 %s，已 %d 天没有日结（应用没开，或日结任务没建、没跑）" % (d.name, files[-1], gap))


def check_status_format(root, out):
    bad = []
    pdir = root / "projects"
    for p in sorted(pdir.iterdir()) if pdir.is_dir() else []:
        f = p / "STATUS.md"
        if not p.is_dir() or p.name.startswith(("_", ".")) or not f.is_file():
            continue
        head = bc.read_text(f).split("\n")[:12]
        indented = any(ln.startswith((" ", "\t")) and ln.strip().startswith(("---", "#", "project:", "generated:", "sources:", "status:")) for ln in head)
        if not head or head[0] != "---" or indented:
            bad.append(p.name)
    if bad:
        out.append("STATUS 格式：%s 首行不是 --- 或开头缩进，下次日汇总会修" % "、".join(bad))


def check_skill_drift(out):
    rec = bc.STATE_DIR / "materialized.json"
    if not rec.is_file():
        return
    try:
        recorded = json.loads(bc.read_text(rec))
    except ValueError:
        return
    drift = [n for n, h in recorded.items() if (bc.SKILLS_DEST / n).is_dir() and bc.bundle_sha256_v2(bc.SKILLS_DEST / n) != h]
    if drift:
        out.append("技能副本漂移：%s 的本机副本被直接改过，同步会拒绝覆盖；把改动合回大脑的 skills/ 再同步" % "、".join(drift))


def problems(root, machine, now=None):
    now = now or datetime.datetime.now()
    runs = run_dates(root)
    out = []
    check_daily(root, now, runs, out)
    check_weekly(root, now, runs, out)
    check_monthly(root, now, runs, out)
    check_inbox(root, machine, now, out)
    check_status_format(root, out)
    check_skill_drift(out)
    return out


def main():
    root = bc.find_root()
    found = problems(root, bc.machine_id(root))
    print("\n".join("%d. %s" % (i, p) for i, p in enumerate(found, 1)) or "ok：无问题")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
