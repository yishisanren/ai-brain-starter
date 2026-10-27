#!/usr/bin/env python3
"""brain_hermes_daily：Hermes 日结，由 default profile 的 19:00 cron 以 --script --no-agent 调用，全程由脚本完成，不需要模型审批。

1. 时间窗：每个 profile 各自从上一次成功日结（自己写过条目，或被列入「无项目工作」行）→ 现在。
   失败的 profile 不前移时间窗，下次从上次成功处重抓，不会因为写了「日结失败」行而丢掉那段会话。
2. 导出 default 与每个专职 profile 在时间窗内的会话（跳过 brain 自己的 cron 与日结会话），压成摘要。
3. 有会话的 profile（含 default）：调用 `hermes [-p <profile>] chat -Q --query-file`，让它按条目格式写自己的日结（只输出，不写文件）。
   没有会话、或写出来只有「无项目工作」的 profile：合并成一行「无项目工作」，正文列出这些 profile。
   失败的 profile：一行「日结失败：<profile>：<原因>」。
4. 每个 profile 的条目先经 brain_write --dry-run 校验（格式、密钥、相似 id），再统一写入 inbox，最后同步公共技能。
   材料放在 ~/.local/state/brain/hermes-staging/<时间>/。
用法：python3 -B brain_hermes_daily.py [--dry-run] [--since auto|"YYYY-MM-DD HH:MM"] [--until "YYYY-MM-DD HH:MM"] [--stamp "YYYY-MM-DD HH:MM"]
      [--max-window-days 14] [--profiles a,b] [--timeout 600] [--workers 3] [--no-materialize]
补跑历史窗口：--profiles 指定失败的 profile，--since/--until 指定窗口，--stamp 写窗口终点让条目落在当天。
退出码：0 写入成功；1 写入失败（条目留在暂存目录 combined_entries.md）。
"""
import argparse
import concurrent.futures
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_common as bc  # noqa: E402

MARKERS = ("#brain-daily-run", "#brain-merge")
BLOCK_RE = re.compile(r"<<<BRAIN-ENTRIES[ \t]*\n(.*?)\n[ \t]*BRAIN-ENTRIES>>>", re.S)
SKILL_DIR = pathlib.Path(os.path.dirname(os.path.abspath(__file__))).parent
SCRIPTS = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))


def hermes_bin():
    return shutil.which("hermes") or str(bc.HOME / ".local" / "bin" / "hermes")


def all_profiles():
    names = ["default"]
    pdir = bc.HOME / ".hermes" / "profiles"
    if pdir.is_dir():
        names += sorted(p.name for p in pdir.iterdir() if not p.name.startswith((".", "_")) and (p / "config.yaml").is_file())
    return names


def cmd(profile, *args):
    c = [hermes_bin()]
    if profile != "default":
        c += ["-p", profile]
    return c + list(args)


def to_dt(v):
    if isinstance(v, (int, float)):
        return datetime.datetime.fromtimestamp(v)
    if isinstance(v, str) and v:
        try:
            dt = datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt.astimezone().replace(tzinfo=None) if dt.tzinfo else dt
        except ValueError:
            try:
                return datetime.datetime.fromtimestamp(float(v))
            except ValueError:
                return None
    return None


def msg_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") in ("text", "input_text", "output_text"))
    return ""


SKIP_SOURCES = ("brain-daily", "brain-probe", "brain-decision")


def state_db(profile):
    base = bc.HOME / ".hermes"
    return base / "state.db" if profile == "default" else base / "profiles" / profile / "state.db"


def db_content(raw):
    if isinstance(raw, str) and raw[:1] in "[{":
        try:
            return msg_text(json.loads(raw))
        except ValueError:
            return raw
    return raw if isinstance(raw, str) else msg_text(raw)


def export_sessions(profile, since, until, timeout):
    """直接只读会话库：`hermes sessions export --newer-than` 只导已结束的会话，
    聊天网关里长期不结束的会话会整段漏掉。库不存在或打不开时退回 CLI 导出。"""
    db = state_db(profile)
    if not db.is_file():
        return export_sessions_cli(profile, since, until, timeout)
    import sqlite3
    con = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=30)
    try:
        rows = con.execute(
            "SELECT s.id, s.source, s.title, s.cwd, m.role, m.content, m.timestamp FROM messages m "
            "JOIN sessions s ON s.id = m.session_id WHERE m.role IN ('user','assistant') "
            "AND m.timestamp >= ? AND m.timestamp <= ? ORDER BY m.timestamp",
            (since.timestamp(), until.timestamp())).fetchall()
        ids = sorted({r[0] for r in rows})
        firsts = {}
        for sid in ids:
            row = con.execute("SELECT content FROM messages WHERE session_id=? AND role='user' ORDER BY timestamp LIMIT 1", (sid,)).fetchone()
            firsts[sid] = bc.clean_text(db_content(row[0])) if row else ""
    finally:
        con.close()
    by = {}
    seen = set()
    for sid, source, title, cwd, role, content, ts in rows:
        if source in SKIP_SOURCES:
            continue
        text = bc.clean_text(db_content(content))
        t = to_dt(ts)
        if not text or t is None:
            continue
        key = (sid, role, text.strip(), t.strftime("%Y%m%d%H%M"))  # 网关会把同一条用户消息存多份
        if key in seen:
            continue
        seen.add(key)
        s = by.setdefault(sid, {"id": sid, "source": source, "title": title or "", "cwd": cwd, "msgs": []})
        s["msgs"].append((t, "U" if role == "user" else "A", text))
    out = []
    for sid, s in by.items():
        # brain 自己的日结 / 汇总 / 周总结会话：第一条用户消息带标记，不算工作
        if any(k in firsts.get(sid, "") for k in MARKERS):
            continue
        s["msgs"].sort(key=lambda x: x[0])
        out.append(s)
    out.sort(key=lambda s: s["msgs"][0][0])
    return out


def export_sessions_cli(profile, since, until, timeout):
    hours = int((until - since).total_seconds() // 3600) + 2
    r = subprocess.run(cmd(profile, "sessions", "export", "-", "--format", "jsonl", "--newer-than", "%dh" % hours),
                       capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError("sessions export 退出码 %d：%s" % (r.returncode, r.stderr.strip()[-300:]))
    sessions = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("source") in SKIP_SOURCES:
            continue
        fallback = to_dt(d.get("last_activity_at")) or to_dt(d.get("started_at"))
        msgs, first_user = [], None
        for m in d.get("messages") or []:
            if not isinstance(m, dict) or m.get("role") not in ("user", "assistant"):
                continue
            text = bc.clean_text(msg_text(m.get("content")))
            if m["role"] == "user" and first_user is None and text:
                first_user = text
            ts = to_dt(m.get("timestamp")) or fallback
            if ts is None or ts < since or ts > until or not text:
                continue
            msgs.append((ts, "U" if m["role"] == "user" else "A", text))
        if not msgs or (first_user and any(k in first_user for k in MARKERS)):
            continue
        msgs.sort(key=lambda x: x[0])
        sessions.append({"id": d.get("id"), "source": d.get("source"), "title": d.get("title") or "",
                         "cwd": d.get("cwd"), "msgs": msgs})
    return sessions


IDLE_RE = re.compile(r"空闲 profile：(.+?)（")


def profile_last_success(root, machine, profile, limit_files=40):
    """该 profile 最近一次成功日结的时间：自己写过条目（不含「日结失败」「会话记录不可读」行），
    或被列入合并的「无项目工作」行。找不到返回 None。"""
    d = root / "inbox" / machine / "hermes"
    if not d.is_dir():
        return None
    mine, shared = "%s/hermes:%s" % (machine, profile), "%s/hermes" % machine
    best = None
    for f in sorted(d.glob("*.md"), reverse=True)[:limit_files]:
        for e in bc.split_entries(bc.read_text(f)):
            if e["kind"] != "日结":
                continue
            field, src = e["project_field"], e["source"]
            if src == mine:
                ok = not field.startswith(("日结失败", "会话记录不可读"))
            elif src == shared and field == "无项目工作":
                m = IDLE_RE.search(e["body"])
                ok = profile in [x.strip() for x in m.group(1).split("、")] if m else True
            else:
                ok = False
            if ok:
                t = bc.parse_time(e["time"])
                if best is None or t > best:
                    best = t
    return best


def resolve_windows(root, machine, profiles, since_arg, until, max_days):
    """每个 profile 的时间窗起点与依据。失败过的 profile 从上次成功处重抓。"""
    if since_arg and since_arg != "auto":
        t = bc.parse_time(since_arg)
        return {p: (t, "指定") for p in profiles}
    fallback, fb_basis = bc.resolve_since(root, machine, "hermes", "auto")
    floor = until - datetime.timedelta(days=max_days)
    out = {}
    for p in profiles:
        t = profile_last_success(root, machine, p)
        basis = "该 profile 上次成功日结"
        if t is None:
            t, basis = fallback, fb_basis
        if t < floor:
            t, basis = floor, basis + "（超过 %d 天，截到上限）" % max_days
        out[p] = (t, basis)
    return out


def header(stamp, field, machine, profile=None):
    src = "%s/hermes" % machine + (":%s" % profile if profile else "")
    return "## %s · 日结 | %s | 来源：%s" % (stamp, field, src)


def profile_prompt(profile, machine, since, until, stamp, digest, root):
    fmt = bc.read_text(SKILL_DIR / "references" / "entry-format.md")
    rows = bc.index_rows(root)
    catalog = "\n".join("- %s（%s）：%s" % (r[0], r[2], bc.redact(r[1])[:50]) for r in rows if len(r) >= 3)
    al = "；".join("%s→%s" % kv for kv in sorted(bc.aliases(root).items()))
    return "\n".join([
        MARKERS[0],
        "你是 Hermes 的「%s」profile。这是 brain 日结任务，由调度脚本统一收集，你只负责写自己的条目。" % profile,
        "下面是你在 %s → %s 之间的会话摘要（已脱敏）。请据此写日结条目。" % (since.strftime(bc.TIME_FMT), until.strftime(bc.TIME_FMT)),
        "",
        "规则：",
        "1. 不调用任何工具，不写任何文件。",
        "2. 只输出条目，并用两个标记行包起来：单独一行 <<<BRAIN-ENTRIES 开始，单独一行 BRAIN-ENTRIES>>> 结束。标记之外不写任何内容。",
        "3. 一个项目一条，标题行：## %s · 日结 | 项目：<项目id> | 来源：%s/hermes:%s" % (stamp, machine, profile),
        "4. 项目 id：先对照下方「已有项目」，同一件事必须复用已有 id（别名换成正式 id）；确实没有、且条目有下一步、阻塞或假设，才新起一个小写字母、数字、连字符的 id，写成「项目：<id>（新）· <一句话>」；一次就做完的事写「项目：misc」。",
        "5. 维度缺就省略；每条正文不超过 25 行；结论标来源等级（工具实测／用户告知／推断）；不写密钥、token、密码、带凭证链接。",
        "6. 本机文件产物写成「- 产物：[文件] <标题> | %s:<绝对路径>（未入库；brain_verify 核实）」；写入前调度脚本会用 brain_verify 实测路径，不存在的产物行会被删掉。不确定路径的不写。" % machine,
        "7. 时间窗内没有任何项目工作（只是闲聊、查询、纯问答）：只输出一行 %s" % header(stamp, "无项目工作", machine, profile),
        "",
        "已有项目（id（状态）：一句话）：",
        catalog or "（暂无）",
        "别名：%s" % (al or "（无）"),
        "",
        "==== 条目格式 ====",
        fmt,
        "",
        "==== 会话摘要 ====",
        digest,
    ])


def run_profile(profile, machine, since, until, stamp, digest, root, stage, timeout, dry):
    """返回 (状态, 条目文本或空, 是否空闲)。条目文本已统一来源、已脱敏。"""
    prompt_path = stage / ("prompt_%s.md" % profile)
    bc.atomic_write(prompt_path, profile_prompt(profile, machine, since, until, stamp, digest, root))
    if dry:
        return "dry-run（未调用）", "", False
    try:
        r = subprocess.run(cmd(profile, "chat", "--query-file", str(prompt_path), "-Q", "--source", "brain-daily",
                               "--max-turns", "3", "--run-budget", str(max(60, timeout - 60)), "--reasoning", "medium"),
                           capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "失败：超时 %ds" % timeout, header(stamp, "日结失败：%s：超时" % profile, machine, profile), False
    bc.atomic_write(stage / ("stdout_%s.txt" % profile), r.stdout + "\n--- stderr ---\n" + r.stderr)
    blocks = BLOCK_RE.findall(r.stdout)
    if r.returncode != 0 or not blocks:
        reason = "退出码 %d" % r.returncode if r.returncode != 0 else "输出里没有条目标记块"
        return "失败：%s" % reason, header(stamp, "日结失败：%s：%s" % (profile, reason), machine, profile), False
    text = bc.redact(blocks[-1].strip())
    expect = "%s/hermes:%s" % (machine, profile)
    fixed = bc.ENTRY_RE.sub(lambda m: "## %s · %s | %s | 来源：%s%s" % (
        m.group(1), m.group(2), m.group(3).strip(), expect, (" | 会话：%s" % m.group(5)) if m.group(5) else ""), text)
    entries = bc.split_entries(fixed)
    if not entries:
        return "失败：条目标题行不合格式", header(stamp, "日结失败：%s：条目标题行不合格式" % profile, machine, profile), False
    fixed = fixed[fixed.find(entries[0]["header"]):].strip()
    if all(e["project_field"] == "无项目工作" for e in entries):
        return "无项目工作", "", True
    return "ok（%d 条）" % len(entries), fixed, False


def validate(text, stage, tag):
    """用 brain_write --dry-run 校验一段条目。返回 (退出码, JSON 或 None)。"""
    p = stage / ("check_%s.md" % tag)
    bc.atomic_write(p, text + "\n")
    r = subprocess.run([sys.executable, "-B", str(SCRIPTS / "brain_write.py"), "--agent", "hermes", "--file", str(p), "--dry-run"],
                       capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    try:
        info = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else None
    except ValueError:
        info = None
    return r.returncode, info


def drop_lines(text, lines):
    keep = [ln for i, ln in enumerate(text.splitlines(), 1) if i not in set(lines)]
    return "\n".join(keep)


def main():
    ap = argparse.ArgumentParser(description="Hermes 日结")
    ap.add_argument("--dry-run", action="store_true", help="只导出摘要、生成提示词，不调模型、不写入")
    ap.add_argument("--since", default="auto", help="auto：每个 profile 各自从上次成功日结起；或指定统一起点")
    ap.add_argument("--until", default="", help="时间窗终点，缺省为现在；补跑历史窗口时指定")
    ap.add_argument("--stamp", default="", help="条目时间戳，缺省为现在；补跑历史窗口时写窗口终点，让条目落在当天")
    ap.add_argument("--max-window-days", type=int, default=14, help="单个 profile 时间窗最长天数，防止长期失败后窗口无限变大")
    ap.add_argument("--profiles", default="")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--max-chars", type=int, default=40000)
    ap.add_argument("--no-materialize", action="store_true")
    ap.add_argument("--no-write", action="store_true", help="调模型、做校验，但不写 inbox（联调用）")
    a = ap.parse_args()

    root = bc.find_root()
    machine = bc.machine_id(root)
    now_dt = datetime.datetime.now()
    until = bc.parse_time(a.until) if a.until else now_dt
    stamp = (bc.parse_time(a.stamp) if a.stamp else bc.now()).strftime(bc.TIME_FMT)
    stage = bc.STATE_DIR / "hermes-staging" / now_dt.strftime("%Y%m%d-%H%M%S")
    stage.mkdir(parents=True, exist_ok=True)
    profiles = [p for p in a.profiles.split(",") if p] or all_profiles()
    windows = resolve_windows(root, machine, profiles, a.since, until, a.max_window_days)
    since = min(w[0] for w in windows.values())

    rows, digests = {}, {}
    for p in profiles:
        rows[p] = {"sessions": -1, "status": "", "entries": "", "idle": False, "warnings": []}
        try:
            sess = export_sessions(p, windows[p][0], until, 180)
            body, _ = bc.fit_render(root, machine, sess, a.max_chars, 800)
            digest = "会话 %d 个。%s" % (len(sess), body if sess else "时间窗内没有会话。")
            bc.atomic_write(stage / ("digest_%s.md" % p), digest)
            digests[p] = digest
            rows[p]["sessions"] = len(sess)
            if not sess:
                rows[p]["status"], rows[p]["idle"] = "无会话", True
        except Exception as exc:  # noqa: BLE001 失败要逐个 profile 记录，不能拖垮整体
            rows[p]["status"] = "失败：导出会话 %s" % str(exc)[:120]
            rows[p]["entries"] = header(stamp, "日结失败：%s：导出会话失败" % p, machine, p)

    todo = [p for p in profiles if rows[p]["sessions"] > 0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, a.workers)) as pool:
        futs = {pool.submit(run_profile, p, machine, windows[p][0], until, stamp, digests[p], root, stage, a.timeout, a.dry_run): p for p in todo}
        for fut in concurrent.futures.as_completed(futs):
            p = futs[fut]
            try:
                rows[p]["status"], rows[p]["entries"], rows[p]["idle"] = fut.result()
            except Exception as exc:  # noqa: BLE001
                rows[p]["status"] = "失败：%s" % str(exc)[:120]
                rows[p]["entries"] = header(stamp, "日结失败：%s：调度异常" % p, machine, p)

    # 逐 profile 校验：格式错误 → 日结失败行；疑似密钥 → 删掉那些行再校验一次
    if not a.dry_run:
        for p in profiles:
            text = rows[p]["entries"]
            if not text or text.startswith("## %s · 日结 | 日结失败" % stamp):
                continue
            code, info = validate(text, stage, p)
            if code == 3 and info and info.get("lines"):
                text = drop_lines(text, info["lines"])
                rows[p]["warnings"].append("删除了 %d 行疑似密钥" % len(info["lines"]))
                code, info = validate(text, stage, p + "-2")
            if code == 2 and info and info.get("artifact_lines"):
                text = drop_lines(text, info["artifact_lines"])
                rows[p]["warnings"].append("删除了 %d 行未通过 brain_verify 的产物" % len(info["artifact_lines"]))
                code, info = validate(text, stage, p + "-3")
            if code != 0:
                detail = (info or {}).get("detail") or (info or {}).get("error") or "退出码 %d" % code
                rows[p]["status"] = "失败：条目校验不通过（%s）" % str(detail)[:100]
                rows[p]["entries"] = header(stamp, "日结失败：%s：条目校验不通过" % p, machine, p)
                continue
            rows[p]["entries"] = text
            rows[p]["warnings"].extend((info or {}).get("warnings") or [])

    idle = [p for p in profiles if rows[p]["idle"]]
    parts = [rows[p]["entries"] for p in profiles if rows[p]["entries"]]
    if idle:
        parts.append(header(stamp, "无项目工作", machine) + "\n- 空闲 profile：%s（时间窗内无会话或无项目工作）" % "、".join(idle))
    combined = "\n\n".join(parts).strip() + "\n"
    bc.atomic_write(stage / "combined_entries.md", combined)

    print(MARKERS[0] + " Hermes 日结")
    print("本机：%s｜时间窗：%s → %s（各 profile 起点见下表）｜条目时间戳：%s" % (machine, since.strftime(bc.TIME_FMT), until.strftime(bc.TIME_FMT), stamp))
    print("暂存目录：%s" % stage)
    print("")
    print("| profile | 起点 | 依据 | 会话数 | 状态 | 提示 |")
    print("|---|---|---|---|---|---|")
    for p in profiles:
        n = rows[p]["sessions"]
        print("| %s | %s | %s | %s | %s | %s |" % (p, windows[p][0].strftime(bc.TIME_FMT), windows[p][1], n if n >= 0 else "?", rows[p]["status"], "；".join(rows[p]["warnings"])))
    if a.dry_run:
        print("\ndry-run：未调模型、未写入。合并后的条目预览：%s" % (stage / "combined_entries.md"))
        return 0
    if a.no_write:
        print("\nno-write：已调模型并校验，未写入。合并后的条目：%s\n" % (stage / "combined_entries.md"))
        print(combined)
        return 0

    r = subprocess.run([sys.executable, "-B", str(SCRIPTS / "brain_write.py"), "--agent", "hermes", "--file", str(stage / "combined_entries.md")],
                       capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
    print("\nbrain_write 退出码 %d：%s" % (r.returncode, (r.stdout.strip() or r.stderr.strip())[-1500:]))
    ok = r.returncode == 0
    if not a.no_materialize:
        m = subprocess.run([sys.executable, "-B", str(SCRIPTS / "brain_materialize.py")],
                           capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
        print("\nbrain_materialize 退出码 %d：%s" % (m.returncode, (m.stdout.strip() or m.stderr.strip())[-800:]))
    failed = [p for p in profiles if rows[p]["status"].startswith("失败")]
    if failed:
        print("\n失败的 profile：%s（已写「日结失败」行，详见暂存目录 stdout_<profile>.txt）" % "、".join(failed))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
