#!/usr/bin/env python3
"""brain_write：把条目追加到 inbox/<本机>/<agent>/<今天>.md。

校验标题行、来源、项目字段、密钥；同机加锁；原子写入；回读校验。
用法：python3 -B brain_write.py --agent claude-code|codex|hermes [--file 条目.md]（省略则读标准输入）[--dry-run]
退出码：0 成功；2 格式或来源错误；3 含疑似密钥（原文未写入）；4 回读不一致。
"""
import argparse
import datetime
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_common as bc  # noqa: E402
import brain_verify  # noqa: E402

SPECIAL_FIELDS = ("无项目工作",)
SPECIAL_PREFIXES = ("会话记录不可读", "日结失败")
ARTIFACT_PATH_RE = re.compile(r"\|\s*([a-z0-9-]+):(/[^（|]+)")


def fail(code, **info):
    info.setdefault("status", "error")
    print(json.dumps(info, ensure_ascii=False))
    sys.exit(code)


def similar_ids(key, known):
    """与已有项目 id 相近的候选：整体相似度高，或连字符分词大半重合。只提示，不拦截。"""
    import difflib
    toks = set(t for t in key.split("-") if len(t) > 1)
    out = []
    for k in sorted(known):
        if k == key:
            continue
        ratio = difflib.SequenceMatcher(None, key, k).ratio()
        ktoks = set(t for t in k.split("-") if len(t) > 1)
        overlap = len(toks & ktoks) / max(1, len(toks | ktoks))
        if ratio >= 0.75 or overlap >= 0.5 or (toks and (toks <= ktoks or ktoks <= toks)):
            out.append(k)
    return out[:3]


def project_id_warnings(key, field, known, aliases):
    """项目 id 的软校验：别名、重复标「新」、与已有项目相似。"""
    out = []
    is_new = "（新）" in field or "(新)" in field
    if key.casefold() in aliases and key not in known:
        out.append("「%s」是别名，正式 id 是「%s」，请改用正式 id" % (key, aliases[key.casefold()]))
        return out
    if key in known:
        if is_new:
            out.append("项目「%s」已存在，不必标（新）" % key)
        return out
    near = similar_ids(key, known)
    if near:
        out.append("新项目 id「%s」与已有项目 %s 相似；如果是同一件事，改用已有 id 重写后再提交" % (key, "、".join("「%s」" % n for n in near)))
    return out


def artifact_error(line, machine):
    """「产物：[文件]」行必须写 brain_verify 核实结果；本机路径当场再用 brain_verify 实测存在。入库行由 brain_store 生成，不查。"""
    s = line.strip()
    if not s.startswith("- 产物：[文件]") or "brain_store" in s:
        return None
    if "brain_verify" not in s:
        return "产物行没有 brain_verify 核实结果：先运行 brain_verify.py <路径>，按输出写「（未入库；brain_verify 核实 <大小> <修改时间>）」；会话记录、ls、摘要列出都不能代替"
    m = ARTIFACT_PATH_RE.search(s)
    if m and m.group(1) == machine and not brain_verify.inspect(m.group(2).strip())["exists"]:
        return "产物路径不存在（brain_verify 实测）：%s" % m.group(2).strip()
    return None


def main():
    ap = argparse.ArgumentParser(description="追加 brain 条目")
    ap.add_argument("--agent", required=True, choices=bc.AGENTS)
    ap.add_argument("--file")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--consume", action="store_true", help="写入并回读成功后删除 --file 指定的临时文件（仅限 ~/.local/state/brain 下）")
    a = ap.parse_args()

    raw = bc.read_text(a.file) if a.file else sys.stdin.read()
    text = raw.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    root = bc.find_root()
    machine = bc.machine_id(root)
    entries = bc.split_entries(text)
    if not entries:
        fail(2, error="format", detail="没有标题行。格式：## YYYY-MM-DD HH:MM · 日结|手动 | 项目：<id> | 来源：<机器>/<agent>[ | 会话：<id>]")
    errors, warnings = [], []
    if text[: text.find(entries[0]["header"])].strip():
        errors.append("第一条标题行之前有多余内容")
    expect = "%s/%s" % (machine, a.agent)
    today = datetime.date.today()
    known = bc.known_projects(root)
    al = bc.aliases(root)
    for e in entries:
        if not (e["source"] == expect or e["source"].startswith(expect + ":")):
            errors.append("来源 %s 与本机本 agent 不符（应为 %s）" % (e["source"], expect))
        field = e["project_field"]
        if field.startswith("项目："):
            key = bc.project_key(field)
            if not bc.SLUG_RE.match(key):
                errors.append("项目 id「%s」必须是小写字母、数字、连字符" % key)
            else:
                warnings.extend(project_id_warnings(key, field, known, al))
        elif field not in SPECIAL_FIELDS and not field.startswith(SPECIAL_PREFIXES):
            errors.append("项目字段不合法：%s" % field)
        if abs((bc.parse_time(e["time"]).date() - today).days) > 1:
            warnings.append("条目时间 %s 与今天相差超过 1 天" % e["time"])
        n = len([ln for ln in e["body"].splitlines() if ln.strip()])
        if n > 25:
            warnings.append("「%s」正文 %d 行，超过 25 行上限" % (field[:40], n))
    art_bad = []
    for i, ln in enumerate(text.splitlines(), 1):
        msg = artifact_error(ln, machine)
        if msg:
            errors.append("第 %d 行%s" % (i, msg))
            art_bad.append(i)
    bad = bc.secret_lines(text)
    if bad:
        fail(3, error="secret", lines=bad, detail="这些行疑似含密钥或凭证，删掉后重试；原文未写入")
    if errors:
        fail(2, error="format", detail=errors, artifact_lines=art_bad)

    target = root / "inbox" / machine / a.agent / (today.isoformat() + ".md")
    if a.dry_run:
        print(json.dumps({"status": "dry-run", "path": str(target), "entries": len(entries), "warnings": warnings}, ensure_ascii=False))
        return
    with bc.FileLock("inbox-%s-%s" % (machine, a.agent), fallback_dir=target.parent) as lock:
        if lock.warning:
            warnings.append(lock.warning)
        old = bc.read_text(target) if target.is_file() else "# inbox · %s/%s · %s\n" % (machine, a.agent, today.isoformat())
        bc.atomic_write(target, old.rstrip("\n") + "\n\n" + text + "\n")
        back = bc.read_text(target)
    if not back.endswith(text + "\n"):
        fail(4, error="readback", path=str(target))
    consumed = False
    if a.consume and a.file:
        src = os.path.realpath(a.file)
        if src.startswith(os.path.realpath(str(bc.STATE_DIR)) + os.sep):
            os.remove(src)
            consumed = True
        else:
            warnings.append("--consume 只删除 ~/.local/state/brain 下的文件，未删除 %s" % a.file)
    print(json.dumps({"status": "ok", "path": str(target), "entries": len(entries),
                      "headers": [e["header"] for e in entries], "lines_before": old.count("\n"),
                      "lines_after": back.count("\n"), "consumed": consumed, "warnings": warnings}, ensure_ascii=False))


if __name__ == "__main__":
    main()
