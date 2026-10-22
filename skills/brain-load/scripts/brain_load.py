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
                if e["project_field"].startswith("项目：") and bc.canonical_project(root, e["project_field"]) == pid:
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

    print("# brain-load 材料")
    print("根目录：%s｜本机：%s｜今天：%s" % (root, machine, today.isoformat()))
    if not pid:
        print("项目：未绑定（%s）" % basis)
        print("\n## 最近项目（INDEX 前 8 行）")
        for row in bc.index_rows(root)[:8]:
            print("- " + " | ".join(row))
        print("\n## 已确认偏好\n" + (pref_text or "（无）"))
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

    print("\n## 已确认偏好\n" + (pref_text or "（无）"))

    entries = inbox_entries(root, pid, [today - datetime.timedelta(days=1), today])
    print("\n## 最近两天 inbox 条目（%d 条；STATUS generated=%s）" % (len(entries), generated or "无"))
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
