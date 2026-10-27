#!/usr/bin/env python3
"""brain_merge_prep：02:00 日汇总的确定性预处理。只读。

扫描 inbox，找出上次处理后新增的条目；切分、脱敏、解析项目 id、标出疑似密钥与格式错误；JSON 输出到 stdout。
_meta/processed.json 由汇总 agent 在全部写入并回读成功后更新；本脚本除 --out 指定的输出文件外不写任何文件。
用法：python3 -B brain_merge_prep.py [--max-entries 400] [--out auto|<路径>]
  --out auto 落盘到 ~/.local/state/brain/merge-prep/<时间>.md（Markdown 摘要：条目全文、编号台账、涉及项目清单）与同名 .json（精简，不含
  context 与 projects 的文件快照），只打印路径与统计。Claude Code 定时任务用：项目台账与全局文件直接 Read 原文件，不内嵌。
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_common as bc  # noqa: E402


GLOBAL_FILES = ["projects/INDEX.md", "_meta/PENDING.md", "_meta/processed.json", "_meta/alerts.json",
                "user/PREFERENCES.md", "lessons/LESSONS.md", "lessons/CORRECTIONS.md", "lessons/INDEX.md", "skills/REGISTRY.md"]
PROJECT_FILES = ["STATUS.md", "DECISIONS.md", "HYPOTHESES.md", "LESSONS.md"]
MAX_CHARS = 20000


def snapshot(path):
    """文件全文（已脱敏）；不存在返回 None；过长截断并注明。"""
    if not path.is_file():
        return None
    text = bc.redact(bc.read_text(path))
    if len(text) > MAX_CHARS:
        return text[:MAX_CHARS] + "\n…（超过 %d 字已截断；需要全文时再读该文件）" % MAX_CHARS
    return text


def main():
    ap = argparse.ArgumentParser(description="brain 日汇总预处理")
    ap.add_argument("--max-entries", type=int, default=400)
    ap.add_argument("--out", default="", help="把 JSON 写到文件而不是 stdout：给路径，或 auto")
    a = ap.parse_args()
    root = bc.find_root()
    processed_path = root / "_meta" / "processed.json"
    done = json.loads(bc.read_text(processed_path)) if processed_path.is_file() else {}
    out = {"generated_at": bc.now().strftime(bc.TIME_FMT), "root": str(root), "files": [], "entries": [],
           "sensitive": [], "malformed": [], "truncated": False}
    base = root / "inbox"
    for f in sorted(base.glob("*/*/*.md")):
        parts = f.relative_to(base).parts
        if any(p.startswith("_") for p in parts):
            continue
        rel = f.relative_to(root).as_posix()
        data = f.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        prev = done.get(rel) or {}
        if prev.get("hash") == digest:
            continue
        entries = bc.split_entries(data.decode("utf-8", errors="replace"))
        if not entries:
            out["malformed"].append({"file": rel, "reason": "没有合法标题行"})
            continue
        start = int(prev.get("entries", 0))
        if start > len(entries):
            out["malformed"].append({"file": rel, "reason": "条目数比上次处理时少（%d<%d），文件被改写过，本次按全部重处理" % (len(entries), start)})
            start = 0
        for i, e in enumerate(entries[start:], start):
            field = e["project_field"]
            bad = bc.secret_lines(e["raw"])
            if bad:
                out["sensitive"].append({"file": rel, "idx": i, "source": e["source"], "lines": bad})
            out["entries"].append({
                "file": rel, "idx": i, "machine": parts[0], "agent": parts[1], "time": e["time"], "kind": e["kind"],
                "project_field": bc.redact(field),
                "project_id": bc.canonical_project(root, field) if field.startswith("项目：") else None,
                "project_is_new": "（新）" in field or "(新)" in field,
                "source": e["source"], "session": e["session"], "body": bc.redact(e["body"]),
            })
        out["files"].append({"file": rel, "hash": digest, "entries": len(entries)})
        if len(out["entries"]) >= a.max_entries:
            out["truncated"] = True
            break
    out["context"] = {rel: snapshot(root / rel) for rel in GLOBAL_FILES}
    index_ids = {row[0] for row in bc.index_rows(root) if row}
    out["projects"] = {}
    for pid in sorted({e["project_id"] for e in out["entries"] if e["project_id"]}):
        pdir = root / "projects" / pid
        hist = pdir / "history"
        out["projects"][pid] = {
            "dir_exists": pdir.is_dir(), "in_index": pid in index_ids,
            "files": {fn: snapshot(pdir / fn) for fn in PROJECT_FILES},
            "history_files": sorted(h.name for h in hist.glob("*.md")) if hist.is_dir() else [],
        }
    out["ids"] = id_ledger(root)
    out["status_format_errors"] = status_format_errors(root)
    out["status_changes"] = status_changes(root, {e["project_id"] for e in out["entries"]})
    out["notes"] = ("context 与 projects 已给出现有文件全文，值为 null 表示文件不存在：直接按 templates.md 新建，"
                    "不要再用 read_file 逐个读取或探测，只有内容被截断时才读对应文件。"
                    "新分配的 D/H/L/B/P 编号必须从 ids.next 给的序号开始顺序往后，全库唯一；ids.conflicts 列出已存在的重号。"
                    "status_format_errors 列出首行不是 --- 或开头被缩进的 STATUS.md，本次顺手重写为顶格。"
                    "status_changes 列出按活跃度自动改状态的项目，照做，不登记待裁定。")
    if a.out:
        import pathlib
        base = (bc.STATE_DIR / "merge-prep" / bc.now().strftime("%Y%m%d-%H%M")) if a.out == "auto" else pathlib.Path(a.out).expanduser().with_suffix("")
        slim = dict(out)
        slim.pop("context", None)
        slim["projects"] = {pid: {k: v for k, v in meta.items() if k != "files"} for pid, meta in out["projects"].items()}
        md = base.with_suffix(".md")
        bc.atomic_write(md, render_digest(out))
        bc.atomic_write(base.with_suffix(".json"), json.dumps(slim, ensure_ascii=False, indent=1))
        print("预处理摘要已写到：%s" % md)
        print("精简 JSON（无文件快照）：%s" % base.with_suffix(".json"))
        print("统计：文件 %d；条目 %d；涉及项目 %d；敏感 %d；格式错误 %d；截断 %s；STATUS 格式问题 %d；自动改状态 %d" % (
            len(out["files"]), len(out["entries"]), len(out["projects"]), len(out["sensitive"]),
            len(out["malformed"]), "是" if out["truncated"] else "否", len(out["status_format_errors"]), len(out["status_changes"])))
        print("项目台账与全局文件请直接 Read brain 根目录下的原文件，摘要里没有内嵌。")
        return
    print(json.dumps(out, ensure_ascii=False, indent=1))


GLOBAL_HINT = ("项目台账（STATUS / DECISIONS / HYPOTHESES / LESSONS）与全局文件（projects/INDEX.md、_meta/PENDING.md、_meta/processed.json、"
               "_meta/alerts.json、user/PREFERENCES.md、lessons/LESSONS.md、lessons/CORRECTIONS.md、lessons/INDEX.md、skills/REGISTRY.md）"
               "请直接 Read 原文件；目录不存在的项目按 templates.md 新建。")


def render_digest(out):
    """给 Claude Code 定时任务看的 Markdown 摘要：条目全文、文件清单、涉及项目、编号台账、格式问题。不内嵌任何文件快照。"""
    L = ["# brain 日汇总预处理 · %s" % out["generated_at"], "", "- 根目录：%s" % out["root"],
         "- 文件 %d；条目 %d；敏感 %d；格式错误 %d；截断 %s；STATUS 格式问题 %d" % (
             len(out["files"]), len(out["entries"]), len(out["sensitive"]), len(out["malformed"]),
             "是" if out["truncated"] else "否", len(out["status_format_errors"])), ""]
    L += ["## 文件（处理成功后按此写 _meta/processed.json）", "", "| 文件 | sha256 | 条目数 |", "|---|---|---|"]
    L += ["| %s | %s | %d |" % (f["file"], f["hash"], f["entries"]) for f in out["files"]] + [""]
    L += ["## 条目（来源键 = 文件#序号；正文已脱敏）", ""]
    for e in out["entries"]:
        tag = "项目 %s%s" % (e["project_id"] or "未解析", "（新）" if e["project_is_new"] else "")
        L += ["### %s#%d · %s · %s · %s/%s · %s" % (e["file"], e["idx"], e["time"], e["kind"], e["machine"], e["agent"], tag), "",
              "标题字段：%s" % e["project_field"],
              "来源：%s%s" % (e["source"], ("｜会话：%s" % e["session"]) if e["session"] else ""), "", e["body"] or "（无正文）", ""]
    for key, title in (("sensitive", "疑似密钥"), ("malformed", "格式错误")):
        L += ["## %s" % title, ""] + (["- %s" % json.dumps(x, ensure_ascii=False) for x in out[key]] or ["无"]) + [""]
    L += ["## 涉及项目", "", "| 项目 id | 目录存在 | 在 INDEX | history 文件 |", "|---|---|---|---|"]
    for pid, m in out["projects"].items():
        L.append("| %s | %s | %s | %s |" % (pid, "是" if m["dir_exists"] else "否", "是" if m["in_index"] else "否", "、".join(m["history_files"]) or "无"))
    L += ["", GLOBAL_HINT, ""]
    ids = out["ids"]
    L += ["## 编号台账", "", "- 今天：%s" % ids["today"], "- 下一个序号：%s" % json.dumps(ids["next"], ensure_ascii=False),
          "- 格式：%s" % ids["format"], "- 今天已用：%s" % json.dumps(ids["used_today"], ensure_ascii=False),
          "- 跨文件重号：%s" % (json.dumps(ids["conflicts"], ensure_ascii=False) if ids["conflicts"] else "无"), ""]
    L += ["## STATUS 格式问题", ""] + (["- %s（首行：%r）" % (x["project"], x["first_line"]) for x in out["status_format_errors"]] or ["无"]) + [""]
    L += ["## 状态自动调整（照做：改 INDEX 状态列与 STATUS frontmatter 的 status）", ""]
    L += (["- %s：%s → %s（%s）" % (x["project"], x["from"], x["to"], x["reason"]) for x in out["status_changes"]] or ["无"]) + [""]
    L += ["## 说明", "", out["notes"], ""]
    return "\n".join(L)


def status_changes(root, entry_pids):
    """按活跃度自动改状态：paused / done 收到新条目转回 active；active 里只有一天记录、下一步为空、
    已过 7 天的转 done；其余 30 天没有新条目的转 paused。活跃度按 history/<日期>.md 的最新日期算。"""
    today = bc.now().date()
    out = []
    pdir = root / "projects"
    for p in sorted(pdir.iterdir()) if pdir.is_dir() else []:
        f = p / "STATUS.md"
        if not p.is_dir() or p.name.startswith(("_", ".")) or not f.is_file():
            continue
        text = bc.read_text(f)
        m = re.search(r"^status:\s*(\S+)", text, re.M)
        status = m.group(1) if m else ""
        if p.name in entry_pids:
            if status in ("paused", "done"):
                out.append({"project": p.name, "from": status, "to": "active", "reason": "收到新条目"})
            continue
        days = sorted(h.stem for h in (p / "history").glob("*.md") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", h.stem))
        if status != "active" or not days:
            continue
        idle = (today - datetime.date.fromisoformat(days[-1])).days
        if len(days) == 1 and idle >= 7 and not bc.section_text(text, "下一步"):
            out.append({"project": p.name, "from": status, "to": "done", "reason": "只有 %s 一天的记录，没有下一步" % days[0]})
        elif idle >= 30:
            out.append({"project": p.name, "from": status, "to": "paused", "reason": "最近条目 %s，%d 天没有新条目" % (days[-1], idle)})
    return out


def status_format_errors(root):
    """首行不是 --- 或开头被缩进的 STATUS.md。模型写文件时偶发整段缩进四个空格，frontmatter 会解析失败。"""
    bad = []
    pdir = root / "projects"
    if not pdir.is_dir():
        return bad
    for p in sorted(pdir.iterdir()):
        f = p / "STATUS.md"
        if not p.is_dir() or p.name.startswith(("_", ".")) or not f.is_file():
            continue
        head = bc.read_text(f).split("\n")[:12]
        indented = any(ln.startswith((" ", "\t")) and ln.strip().startswith(("---", "#", "project:", "generated:", "sources:", "status:")) for ln in head)
        if not head or head[0] != "---" or indented:
            bad.append({"project": p.name, "first_line": (head[0] if head else "")[:40]})
    return bad


ID_RE = re.compile(r"\b([DHLBP])-(\d{4}-\d{2}-\d{2})-(\d{2,})\b")
ID_FILES = {
    "D": ["_meta/PENDING.md"], "P": ["user/PREFERENCES.md"], "B": ["lessons/CORRECTIONS.md"],
    "L": ["lessons/LESSONS.md", "projects/*/LESSONS.md"], "H": ["projects/*/HYPOTHESES.md"],
}


def id_ledger(root):
    """全库已用编号：每类每天的最大序号、今天的下一个序号、跨文件重号。编号只在定义它的台账文件里数，STATUS 等引用不算。"""
    today = bc.now().strftime("%Y-%m-%d")
    used = {}
    where = {}
    for kind, pats in ID_FILES.items():
        for pat in pats:
            for f in sorted(root.glob(pat)):
                if not f.is_file() or any(part.startswith(("_", ".")) for part in f.relative_to(root).parts[:-1]):
                    continue
                for m in ID_RE.finditer(bc.read_text(f)):
                    if m.group(1) != kind:
                        continue
                    full = m.group(0)
                    used.setdefault(kind, {}).setdefault(m.group(2), set()).add(int(m.group(3)))
                    where.setdefault(full, set()).add(f.relative_to(root).as_posix())
    nxt = {}
    for kind in ID_FILES:
        nxt[kind] = max(used.get(kind, {}).get(today, {0})) + 1
    conflicts = {k: sorted(v) for k, v in where.items() if len(v) > 1}
    return {"today": today, "next": nxt,
            "format": "<类型>-<今天 YYYY-MM-DD>-<两位序号>，例如 H-%s-%02d" % (today, nxt["H"]),
            "used_today": {k: sorted(used.get(k, {}).get(today, [])) for k in ID_FILES},
            "conflicts": conflicts}


if __name__ == "__main__":
    main()
