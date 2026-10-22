#!/usr/bin/env python3
"""brain_find：按描述在 brain/artifacts/INDEX.md 里找产物，核实本机文件，输出候选。只读，不改任何文件。

用法：
  python3 -B brain_find.py --q "去广告 插件包" [--project <id或别名>] [--since YYYY-MM-DD] [--limit 3]
  python3 -B brain_find.py --id A-2026-09-23-01
  python3 -B brain_find.py --list [--project <id或别名>] [--limit 20]
输出：第一行 JSON（候选数组：id、标题、项目、类型、abs_path 或 url、verify、score），随后是人读的表。
verify：ok 本机存在且 md5 一致；missing 索引有但本机没有；md5-mismatch 内容已变；link 链接类不核实。
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_common as bc  # noqa: E402

COLUMNS = 10
CJK_RE = re.compile(r"[一-鿿]")
SPLIT_RE = re.compile(r"[\s,，。、;；/|「」『』（）()\[\]【】\"'“”‘’]+")
STOP = {"之前", "那个", "上次", "上周", "昨天", "文件", "发我", "给我", "发给我", "一下", "存的", "保存的", "保存", "存过", "帮我", "把", "的", "了",
        "the", "a", "an", "file", "that", "please"}
MD5_LIMIT = 500 * 1024 * 1024


def index_rows(root):
    p = root / "artifacts" / "INDEX.md"
    if not p.is_file():
        return []
    rows = []
    for rs in bc.md_sections(bc.read_text(p)).values():
        rows.extend(r for r in rs if len(r) >= COLUMNS and r[0].startswith("A-"))
    return rows


STOP_SUBSTR = ("之前存的", "之前保存的", "上次存的", "之前", "那个", "那份", "上次", "上周", "昨天", "发给我", "发我", "给我", "帮我", "找一下", "一下", "保存的", "存的", "存过的", "文件")


def tokens(q):
    q = q.strip().casefold()
    for w in STOP_SUBSTR:
        q = q.replace(w, " ")
    q = re.sub(r"(?<=[\u4e00-\u9fff])[的把了吗呢啊]+(?=[\u4e00-\u9fff]|$)", " ", q)
    parts = [t for t in SPLIT_RE.split(q) if t and t not in STOP]
    full, grams = [], []
    for t in parts:
        full.append(t)
        if CJK_RE.search(t) and len(t) >= 3:
            grams.extend(t[i:i + 2] for i in range(len(t) - 1))
    return list(dict.fromkeys(full)), [g for g in dict.fromkeys(grams) if g not in full and g not in STOP]


def score(row, full, grams, q):
    title, project, note = row[3].casefold(), row[2].casefold(), row[9].casefold()
    where = (row[5] + " " + row[7]).casefold()
    s = 0.0
    for t in full:
        if t in title:
            s += 4
        if t in project or t in project.replace("-", ""):
            s += 3
        if t in note:
            s += 2
        if t in where:
            s += 1
    for g in grams:
        if g in title:
            s += 1
        elif g in note:
            s += 0.5
    qn = re.sub(r"\s+", "", q.casefold())
    for hay, w in ((title.replace(" ", ""), 1.5), (note.replace(" ", ""), 0.8)):
        m = difflib.SequenceMatcher(None, qn, hay).find_longest_match(0, len(qn), 0, len(hay))
        if m.size >= 2:
            s += min(6.0, m.size * w)
    s += 3 * difflib.SequenceMatcher(None, q.casefold(), title).ratio()
    return round(s, 2)


def md5_of(path):
    h = hashlib.md5()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(root, row):
    if row[4] == "链接":
        return {"verify": "link", "url": row[5]}
    p = root / row[5]
    out = {"abs_path": str(p)}
    if not p.is_file():
        out["verify"] = "missing"
        return out
    size = p.stat().st_size
    out["size"] = size
    m = re.search(r"md5 ([0-9a-f]{12})", row[6])
    if m and size <= MD5_LIMIT:
        out["verify"] = "ok" if md5_of(p).startswith(m.group(1)) else "md5-mismatch"
    else:
        out["verify"] = "ok" if p.is_file() else "missing"
    return out


def as_json(root, row, s=None):
    d = {"id": row[0], "date": row[1], "project": row[2], "title": row[3], "kind": row[4], "pointer": row[5],
         "check": row[6], "origin": row[7], "source": row[8], "note": row[9]}
    if s is not None:
        d["score"] = s
    d.update(verify(root, row))
    return d


def main():
    ap = argparse.ArgumentParser(description="在 brain 产物库里找东西")
    ap.add_argument("--q", default="", help="描述关键词，空格分开")
    ap.add_argument("--id", default="", help="按 id 精确取")
    ap.add_argument("--list", action="store_true", help="列最近的产物")
    ap.add_argument("--project", default="", help="限定项目 id 或别名")
    ap.add_argument("--since", default="", help="只看产出日期不早于这天的：YYYY-MM-DD")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    if not (a.q or a.id or a.list):
        ap.error("给 --q、--id 或 --list 之一")

    root = bc.find_root()
    rows = index_rows(root)
    pid = ""
    if a.project:
        pid = bc.canonical_project(root, a.project) or a.project
        rows = [r for r in rows if r[2] == pid]
    if a.since:
        rows = [r for r in rows if r[1] >= a.since or r[0][2:12] >= a.since]

    if a.id:
        hits = [as_json(root, r) for r in rows if r[0] == a.id]
    elif a.list:
        hits = [as_json(root, r) for r in list(reversed(rows))[: a.limit or 20]]
    else:
        full, grams = tokens(a.q)
        scored = [(score(r, full, grams, a.q), r) for r in rows]
        scored = [(s, r) for s, r in scored if s >= 2.5]
        scored.sort(key=lambda x: (-x[0], x[1][0]))
        hits = [as_json(root, r, s) for s, r in scored[: a.limit or 3]]

    print(json.dumps({"query": a.q or a.id or "list", "project": pid, "index": str(root / "artifacts" / "INDEX.md"),
                      "total_rows": len(rows), "hits": hits}, ensure_ascii=False))
    if not hits:
        print("产物库里没有匹配项（索引 %d 行%s）。换关键词，或 --list --project <id> 看该项目全部。" % (len(rows), "，已限定项目 " + pid if pid else ""))
        return
    print("| id | 产出日期 | 项目 | 标题 | 类型 | 本机路径 / URL | 核实 |")
    print("|---|---|---|---|---|---|---|")
    for h in hits:
        print("| %s | %s | %s | %s | %s | %s | %s |" % (h["id"], h["date"], h["project"], h["title"], h["kind"],
                                                       h.get("abs_path") or h.get("url"), h["verify"]))


if __name__ == "__main__":
    main()
