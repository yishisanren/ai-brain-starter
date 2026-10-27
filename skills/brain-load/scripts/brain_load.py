#!/usr/bin/env python3
"""brain_load：为开工简报收集原始材料。只读。

用法：python3 -B brain_load.py [--project 项目名或id] [--cwd 目录]
"""
import argparse
import datetime
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_common as bc  # noqa: E402
import brain_watchdog  # noqa: E402

LOOKBACK_DAYS = 14  # shortcut: 没汇总过只回看 14 天；更早的要靠日汇总折进 STATUS


def days_since(start, today):
    return [start + datetime.timedelta(days=i) for i in range((today - start).days + 1)]


def frontmatter_value(text, key):
    m = re.search(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return ""
    for line in m.group(1).splitlines():
        if line.startswith(key + ":"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


def inbox_entries(root, pid, days):
    base = root / "inbox"
    out = []
    if not base.is_dir():
        return out
    for day in days:
        for f in base.glob("*/*/%s.md" % day.isoformat()):
            if any(part.startswith("_") for part in f.relative_to(base).parts):
                continue
            for e in bc.split_entries(bc.read_text(f)):
                if e["project_field"].startswith("项目：") and (pid is None or bc.canonical_project(root, e["project_field"]) == pid):
                    out.append(e)
    out.sort(key=lambda e: e["time"])
    return out


def artifact_rows(root):
    p = root / "artifacts" / "INDEX.md"
    if not p.is_file():
        return []
    rows = []
    for rs in bc.md_sections(bc.read_text(p)).values():
        rows.extend(r for r in rs if len(r) >= 10 and r[0].startswith("A-"))
    return rows


def table_rows(path):
    if not path.is_file():
        return []
    rows = []
    for rs in bc.md_sections(bc.read_text(path)).values():
        rows.extend(r for r in rs if any(c.strip() not in bc.PLACEHOLDERS for c in r))
    return rows


SCOPE_RE = re.compile(r"范围：([a-z0-9][a-z0-9-]*)")


def scoped_prefs(root, text, pid):
    """只留全局、按主题和本项目的偏好；范围是别的项目 id 的略去。返回 (文本, 略去条数)。"""
    known = bc.known_projects(root)
    keep, skipped = [], 0
    for line in text.splitlines():
        m = SCOPE_RE.search(line)
        cid = bc.canonical_project(root, m.group(1)) if m else None
        if cid and cid in known and cid != pid:
            skipped += 1
            continue
        keep.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(keep)).strip(), skipped


def lesson_field(block, name):
    m = re.search(r"^- %s：(.*)$" % name, block, re.M)
    return m.group(1).strip() if m else ""


def project_lessons(root, pid, cap=5):
    """本项目经验：projects/<id>/LESSONS.md 加通用库里来源是本项目的；跳过已失效，按 id 取最新 cap 条。"""
    blocks = []
    for path, own in ((root / "projects" / pid / "LESSONS.md", True), (root / "lessons" / "LESSONS.md", False)):
        if not path.is_file():
            continue
        for b in re.split(r"\n(?=### L-)", bc.read_text(path)):
            if not b.startswith("### L-") or "已失效" in lesson_field(b, "状态"):
                continue
            if own or "（项目 %s）" % pid in lesson_field(b, "来源"):
                blocks.append(b)
    blocks.sort(key=lambda b: b.split()[1])
    return blocks[-cap:]


def main():
    ap = argparse.ArgumentParser(description="brain 开工材料")
    ap.add_argument("--project", default="")
    ap.add_argument("--cwd", default="")
    a = ap.parse_args()
    root = bc.find_root()
    machine = bc.machine_id(root)
    today = datetime.date.today()
    pid, basis = bc.resolve_project(root, machine, a.project or None, a.cwd or os.getcwd())
    prefs = root / "user" / "PREFERENCES.md"
    pref_text = bc.section_text(bc.read_text(prefs), "已确认") if prefs.is_file() else ""
    pref_text, pref_skipped = scoped_prefs(root, pref_text, pid)
    pref_title = "\n## 已确认偏好（全局与本项目；其他项目范围的 %d 条已略）\n" % pref_skipped

    print("# brain-load 材料")
    print("根目录：%s｜本机：%s｜今天：%s" % (root, machine, today.isoformat()))
    alerts = brain_watchdog.problems(root, machine)
    if alerts:
        print("\n## 自动运行提醒（简报里照实告诉用户）\n" + "\n".join("- " + a for a in alerts))
    if not pid:
        print("项目：未绑定（%s）" % basis)
        latest = {}
        for e in inbox_entries(root, None, days_since(today - datetime.timedelta(days=LOOKBACK_DAYS), today)):
            latest[bc.canonical_project(root, e["project_field"])] = e  # 按时间排好，后写的覆盖
        latest.pop(None, None)
        print("\n## 最近有记录的项目（新的在前）")
        rows = sorted(latest.items(), key=lambda kv: kv[1]["time"], reverse=True)[:8]
        print("\n".join("- %s · 最近一条 %s · 来源 %s" % (p, e["time"], e["source"]) for p, e in rows) or "（无）")
        print("\n## 最近项目（INDEX 前 8 行）")
        for row in bc.index_rows(root)[:8]:
            print("- " + " | ".join(row))
        print(pref_title + (pref_text or "（无）"))
        return

    print("项目：%s（依据：%s）" % (pid, basis))
    pdir = root / "projects" / pid
    generated = ""
    print("\n## STATUS.md")
    if (pdir / "STATUS.md").is_file():
        st = bc.read_text(pdir / "STATUS.md")
        generated = frontmatter_value(st, "generated")
        print(st.strip())
    else:
        print("（尚无 STATUS.md：该项目还没有汇总过）")

    print(pref_title + (pref_text or "（无）"))

    print("\n## 本项目经验（最新 5 条，已失效的不列）")
    lessons = project_lessons(root, pid)
    print("\n".join("- %s · %s → %s（%s，出现 %s）" % (
        b.split()[1], lesson_field(b, "场景"), lesson_field(b, "做法"), lesson_field(b, "状态"), lesson_field(b, "出现").split("（")[0])
        for b in lessons) or "（无）")

    # 近 30 天的更正已在 STATUS「已更正」段，这里补掉出 STATUS 的更早偏差
    cutoff = (today - datetime.timedelta(days=30)).isoformat()
    print("\n## 本项目更早的偏差（30 天前，最近 5 条）")
    old = [r for r in table_rows(root / "lessons" / "CORRECTIONS.md") if len(r) >= 8 and r[2] == pid and r[1][:10] < cutoff]
    print("\n".join("- %s · %s · %s：%s → %s（根因：%s）" % (r[0], r[1], r[3], r[4], r[6], r[5]) for r in old[-5:]) or "（无）")

    start = today - datetime.timedelta(days=LOOKBACK_DAYS)
    try:
        start = max(start, datetime.date.fromisoformat(generated[:10]))
    except ValueError:
        pass
    entries = inbox_entries(root, pid, days_since(start, today))
    print("\n## 尚未汇总的 inbox 条目（%d 条，自 %s 起；STATUS generated=%s）" % (len(entries), start.isoformat(), generated or "无"))
    for e in entries:
        merged = generated and e["time"] <= generated[:16]
        print("\n" + ("【STATUS 生成前已有】" if merged else "【尚未合并】"))
        print(e["raw"])

    print("\n## DECISIONS 最后 5 行")
    drows = table_rows(pdir / "DECISIONS.md")
    print("\n".join("| " + " | ".join(r) + " |" for r in drows[-5:]) or "（无）")

    print("\n## 到期待回填的假设")
    due = []
    for row in table_rows(pdir / "HYPOTHESES.md"):
        if len(row) >= 8 and "待验证" in row[7]:
            try:
                if datetime.date.fromisoformat(row[4].strip()[:10]) <= today:
                    due.append(row)
            except ValueError:
                pass
    print("\n".join("| " + " | ".join(r) + " |" for r in due) or "（无）")

    print("\n## 待裁定（本项目）")
    pend = [r for r in table_rows(root / "_meta" / "PENDING.md") if len(r) >= 7 and r[2] == pid and "已处理" not in r[6]]
    print("\n".join("| " + " | ".join(r) + " |" for r in pend) or "（无）")

    print("\n## 本项目产物（artifacts/INDEX.md 最近 5 条；找回用 brain-find）")
    arts = [r for r in artifact_rows(root) if r[2] == pid]
    print("\n".join("- %s · %s · %s · %s · %s" % (r[0], r[1], r[3], r[4], r[5]) for r in arts[-5:][::-1]) or "（无）")


if __name__ == "__main__":
    main()
