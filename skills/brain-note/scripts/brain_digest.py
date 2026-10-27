#!/usr/bin/env python3
"""brain_digest：把 Claude Code 或 Codex 在时间窗内的会话压成摘要，供 brain-note 日结模式写条目。只读。

用法：python3 -B brain_digest.py --agent claude-code|codex [--since auto|"YYYY-MM-DD HH:MM"] [--until "YYYY-MM-DD HH:MM"]
      [--max-chars 60000] [--per-msg 1200]
"""
import argparse
import datetime
import glob
import json
import os
import pathlib
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_common as bc  # noqa: E402

MARKERS = ("#brain-daily-run", "#brain-merge")  # 日结任务和汇总任务的提示词都以这两个标记开头


def to_local(ts):
    if not isinstance(ts, str) or not ts:
        return None
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.astimezone().replace(tzinfo=None) if dt.tzinfo else dt


def claude_text(content):
    if isinstance(content, str):
        return bc.clean_text(content)
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        return bc.clean_text("\n".join(p for p in parts if p))
    return ""


def is_daily_run(first_user_text):
    """大脑自己的定时任务会话（日结、汇总）：第一条用户消息里就带标记。
    只看第一条，不看时间窗内的任何一条：讨论 brain 的工作会话后面也会出现这个标记，不能整场跳过。"""
    return bool(first_user_text) and any(m in first_user_text for m in MARKERS)


def claude_sessions(since, until):
    sessions = {}
    for path in (bc.HOME / ".claude" / "projects").glob("*/*.jsonl"):
        try:
            if datetime.datetime.fromtimestamp(path.stat().st_mtime) < since:
                continue
        except OSError:
            continue
        first_user = None
        file_sessions = set()
        with open(str(path), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                kind = d.get("type")
                if kind not in ("user", "assistant") or d.get("isSidechain") or d.get("isMeta"):
                    continue
                text = claude_text((d.get("message") or {}).get("content"))
                if kind == "user" and first_user is None and text:
                    first_user = text
                ts = to_local(d.get("timestamp"))
                if ts is None or ts < since or ts > until or not text:
                    continue
                sid = d.get("sessionId") or path.stem
                s = sessions.setdefault(sid, {"id": sid, "cwd": d.get("cwd"), "msgs": [], "skip": ""})
                file_sessions.add(sid)
                s["cwd"] = s["cwd"] or d.get("cwd")
                s["msgs"].append((ts, "U" if kind == "user" else "A", text))
        if is_daily_run(first_user):
            for sid in file_sessions:
                sessions[sid]["skip"] = "大脑任务自身"
    return list(sessions.values())


INJECT_TAG_RE = re.compile(r"^<([A-Za-z_][A-Za-z0-9_-]*)(\\s[^>]*)?>")


def codex_block_text(block):
    """Codex response_item 的文本块；滤掉注入的上下文（AGENTS.md、环境信息、插件清单等）。"""
    if not isinstance(block, dict) or block.get("type") not in ("input_text", "output_text", "text"):
        return ""
    text = block.get("text") or ""
    head = text.lstrip()
    if head.startswith("# AGENTS.md instructions") or INJECT_TAG_RE.match(head):
        return ""
    return text


def codex_files(since):
    """按修改时间筛选全部日期目录下的会话文件：长期使用的老会话也会被扫到。"""
    base = bc.HOME / ".codex" / "sessions"
    cutoff = since.timestamp()
    out = []
    for fp in glob.glob(str(base / "*" / "*" / "*" / "rollout-*.jsonl")):
        try:
            if os.path.getmtime(fp) >= cutoff:
                out.append(fp)
        except OSError:
            continue
    return sorted(out)


def codex_sessions(since, until):
    out = []
    for fp in codex_files(since):
        s = {"id": pathlib.Path(fp).stem[-36:], "cwd": None, "msgs": [], "skip": ""}
        events, items = [], []
        first_user = None
        with open(fp, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                p = d.get("payload") if isinstance(d.get("payload"), dict) else {}
                kind = d.get("type")
                if kind == "session_meta":
                    s["id"] = p.get("id") or s["id"]
                    s["cwd"] = p.get("cwd") or s["cwd"]
                    if isinstance(p.get("source"), dict) and "subagent" in p["source"]:
                        s["skip"] = "子代理"
                    continue
                if kind == "turn_context":
                    s["cwd"] = p.get("cwd") or s["cwd"]
                    continue
                if kind == "event_msg" and p.get("type") in ("user_message", "agent_message"):
                    ts = to_local(d.get("timestamp"))
                    text = bc.clean_text(p.get("message"))
                    if p.get("type") == "user_message" and first_user is None and text:
                        first_user = text
                    if ts is not None and since <= ts <= until and text:
                        events.append((ts, "U" if p.get("type") == "user_message" else "A", text))
                elif kind == "response_item" and p.get("type") == "message" and p.get("role") in ("user", "assistant"):
                    ts = to_local(d.get("timestamp"))
                    text = bc.clean_text("\n".join(x for x in (codex_block_text(b) for b in (p.get("content") or [])) if x))
                    if p.get("role") == "user" and first_user is None and text:
                        first_user = text
                    if ts is not None and since <= ts <= until and text:
                        items.append((ts, "U" if p.get("role") == "user" else "A", text))
        if not s["skip"] and is_daily_run(first_user):
            s["skip"] = "大脑任务自身"
        seen, merged = set(), []
        for m in sorted(events + items, key=lambda x: x[0]):
            key = (m[1], m[2].strip(), m[0].strftime("%Y%m%d%H%M"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(m)
        s["msgs"] = merged
        out.append(s)
    return out


ARTIFACT_EXT = {".zip", ".apk", ".ipa", ".html", ".pdf", ".docx", ".xlsx", ".pptx", ".csv", ".tar", ".gz", ".tgz", ".dmg", ".pkg", ".mcpb", ".skill", ".png", ".jpg", ".mp4"}


def _in_window(path, since, until):
    try:
        t = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    except OSError:
        return False
    return since <= t <= until


def claude_sent_files(since, until):
    """Claude Code 会话里发给用户的文件（SendUserFile），以及写出的交付型文件（Write，按扩展名筛）。"""
    out = {}
    for path in (bc.HOME / ".claude" / "projects").glob("*/*.jsonl"):
        try:
            if datetime.datetime.fromtimestamp(path.stat().st_mtime) < since:
                continue
        except OSError:
            continue
        with open(str(path), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"tool_use"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") != "assistant" or d.get("isSidechain"):
                    continue
                ts = to_local(d.get("timestamp"))
                if ts is None or ts < since or ts > until:
                    continue
                for blk in (d.get("message") or {}).get("content") or []:
                    if not isinstance(blk, dict) or blk.get("type") != "tool_use":
                        continue
                    inp = blk.get("input") or {}
                    files = []
                    if blk.get("name") == "SendUserFile":
                        files = inp.get("files") or []
                    elif blk.get("name") == "Write" and os.path.splitext(str(inp.get("file_path", "")))[1].lower() in ARTIFACT_EXT:
                        files = [inp["file_path"]]
                    for f in files:
                        f = os.path.abspath(os.path.expanduser(str(f)))
                        out.setdefault(f, "SendUserFile" if blk.get("name") == "SendUserFile" else "Write")
    return out


def codex_output_files(since, until):
    """Codex 桌面版每个会话的 outputs/ 目录：里面的东西默认就是交付物。"""
    out = {}
    for fp in glob.glob(str(bc.HOME / "Documents" / "Codex" / "*" / "*" / "outputs" / "**" / "*"), recursive=True):
        if os.path.isfile(fp) and not os.path.basename(fp).startswith(".") and _in_window(fp, since, until):
            out[os.path.abspath(fp)] = "Codex outputs"
    return out


def candidate_artifacts(root, machine, agent, since, until):
    """时间窗内新出现、还没进产物库的文件。只列出来供归条目时写「未入库」指针；入库由用户说「存一下」触发。"""
    found = claude_sent_files(since, until) if agent == "claude-code" else codex_output_files(since, until)
    idx = root / "artifacts" / "INDEX.md"
    known = bc.read_text(idx) if idx.is_file() else ""
    vault = str(root.parent.parent)
    lines = ["", "## 候选产物（时间窗内新出现、未入库；只在条目里记指针，不自动入库）"]
    n = 0
    for f in sorted(found):
        if not os.path.isfile(f) or f.startswith(vault) or ("%s:%s" % (machine, f)) in known:
            continue
        n += 1
        try:
            st = os.stat(f)
            meta = "%s · %s" % (datetime.datetime.fromtimestamp(st.st_mtime).strftime("%m-%d %H:%M"), "%.1fKB" % (st.st_size / 1024.0))
        except OSError:
            meta = "?"
        lines.append("- %s:%s（%s；来自 %s）" % (machine, f, meta, found[f]))
    if n == 0:
        lines.append("（无）")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="brain 会话摘要（Claude Code / Codex）")
    ap.add_argument("--agent", required=True, choices=("claude-code", "codex"))
    ap.add_argument("--since", default="auto")
    ap.add_argument("--until", default="")
    ap.add_argument("--max-chars", type=int, default=60000)
    ap.add_argument("--per-msg", type=int, default=1200)
    a = ap.parse_args()

    root = bc.find_root()
    machine = bc.machine_id(root)
    since, basis = bc.resolve_since(root, machine, a.agent, a.since)
    until = bc.parse_time(a.until) if a.until else datetime.datetime.now()
    raw = claude_sessions(since, until) if a.agent == "claude-code" else codex_sessions(since, until)

    skipped = {"大脑任务自身": 0, "子代理": 0, "时间窗内无对话": 0}
    kept = []
    for s in raw:
        if s["skip"]:
            skipped[s["skip"]] += 1
        elif not s["msgs"]:
            skipped["时间窗内无对话"] += 1
        else:
            s["msgs"].sort(key=lambda m: m[0])
            s["project"] = bc.project_for_cwd(root, machine, s["cwd"])
            kept.append(s)
    kept.sort(key=lambda s: s["msgs"][0][0])
    body, cap = bc.fit_render(root, machine, kept, a.max_chars, a.per_msg)

    print("# 会话摘要 · %s/%s" % (machine, a.agent))
    print("时间窗：%s → %s（起点依据：%s）" % (since.strftime(bc.TIME_FMT), until.strftime(bc.TIME_FMT), basis))
    print("会话：%d 个；跳过：%s；单条上限 %d 字；疑似密钥已脱敏" % (
        len(kept), "，".join("%s %d" % kv for kv in skipped.items()), cap))
    if not kept:
        print("\n时间窗内没有可沉淀的会话。日结只写一行「无项目工作」。")
    print(body)
    print(project_catalog(root))
    print(candidate_artifacts(root, machine, a.agent, since, until))


def project_catalog(root):
    """已有项目清单，附在摘要末尾：写条目时先在这里找，能对上的就复用 id，不要另起新项目。"""
    lines = ["", "## 已有项目（写条目时先对照这份清单；同一件事复用已有 id，不要另起 id）",
             "| 项目 id | 状态 | 一句话 |", "|---|---|---|"]
    rows = bc.index_rows(root)
    order = {"active": 0, "未迁移": 1, "done": 2, "已停用": 3}
    for row in sorted(rows, key=lambda r: (order.get(r[2] if len(r) > 2 else "", 9), r[0])):
        if len(row) < 3:
            continue
        lines.append("| %s | %s | %s |" % (row[0], row[2], bc.redact(row[1])[:60]))
    al = bc.aliases(root)
    if al:
        lines.append("别名 → 正式 id：" + "；".join("%s→%s" % kv for kv in sorted(al.items())))
    return "\n".join(lines)


if __name__ == "__main__":
    main()
