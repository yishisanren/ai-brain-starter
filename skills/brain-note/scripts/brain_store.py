#!/usr/bin/env python3
"""brain_store：把交付物存进 brain/artifacts/<项目>/，登记 artifacts/INDEX.md，并追加一条 inbox「手动」条目。

用户说「存一下」「保存起来」「保存这些」时由 agent 调用。文件复制后回读 md5 校验；目录先打成 zip；云文档只记链接。
用法：
  python3 -B brain_store.py --agent claude-code|codex --project <id或别名> --title "<一句人话标题>" \
      [--note "<备注>"] [--session <会话id>] [--dry-run] <路径> [<路径> ...]
  python3 -B brain_store.py --agent ... --project <id> --title "<标题>" --link <URL>
退出码：0 成功；2 参数、项目 id 或格式错误；3 文本文件或链接含疑似密钥（未写入）；4 复制或回读校验失败。
输出一行 JSON：ids、stored（库内路径、md5、大小）、entry_lines（写进 inbox 的产物行）、inbox、warnings。
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_common as bc  # noqa: E402
import brain_verify  # noqa: E402
import brain_write  # noqa: E402

INDEX_COLUMNS = ["id", "产出日期", "项目", "标题", "类型", "指针", "校验", "原位置", "来源", "备注"]
INDEX_HEAD = ("---\ntitle: 产物索引\nupdated: %s\n---\n"
              "# 产物索引（各 agent 经 brain_store.py 追加；找回用 brain-find，不手工编辑）\n\n"
              "id 形如 A-<入库日期>-<序号>。指针是相对 brain 根目录的路径或 URL；校验为 md5 前 12 位与字节数。\n\n"
              "| " + " | ".join(INDEX_COLUMNS) + " |\n|" + "---|" * len(INDEX_COLUMNS) + "\n")
TEXT_SCAN_LIMIT = 2 * 1024 * 1024
SIZE_WARN = 50 * 1024 * 1024
UNSAFE_RE = re.compile(r"[\\/:*?\"<>|\s\u3000·•・]+")


def fail(code, **info):
    info.setdefault("status", "error")
    print(json.dumps(info, ensure_ascii=False))
    sys.exit(code)


def cell(s):
    return str(s).replace("|", "｜").replace("\n", " ").strip() or "—"


def index_path(root):
    return root / "artifacts" / "INDEX.md"


def index_rows(root):
    p = index_path(root)
    if not p.is_file():
        return []
    rows = []
    for rs in bc.md_sections(bc.read_text(p)).values():
        rows.extend(r for r in rs if len(r) >= len(INDEX_COLUMNS) and r[0].startswith("A-"))
    return rows


def next_id(rows, today):
    prefix = "A-%s-" % today.isoformat()
    n = 0
    for r in rows:
        if r[0].startswith(prefix):
            try:
                n = max(n, int(r[0][len(prefix):]))
            except ValueError:
                pass
    return "%s%02d" % (prefix, n + 1)


def slug(title, limit=50):
    s = UNSAFE_RE.sub("-", bc.nfc(title)).strip("-.")
    s = re.sub(r"-{2,}", "-", s)
    return (s[:limit].rstrip("-.") or "untitled")


def md5_of(path):
    h = hashlib.md5()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%d%s" % (n, unit)) if unit == "B" else ("%.1f%s" % (n, unit))
        n /= 1024.0
    return str(n)


def text_secret_lines(path, size):
    """小于 2MB 且能按 utf-8 解码的文件才扫；其余视为二进制，不扫。返回 (行号列表, 是否扫过)。"""
    if size > TEXT_SCAN_LIMIT:
        return [], False
    try:
        text = pathlib.Path(path).read_bytes().decode("utf-8")
    except (UnicodeDecodeError, OSError):
        return [], False
    return bc.secret_lines(text), True


def produced_date(path):
    p = pathlib.Path(path)
    latest = p.stat().st_mtime
    if p.is_dir():
        n = 0
        for dirpath, dirnames, filenames in os.walk(str(p)):
            dirnames[:] = [d for d in dirnames if d not in bc._IGN_DIRS]
            for fn in filenames:
                n += 1
                if n > 2000:
                    break
                try:
                    latest = max(latest, os.path.getmtime(os.path.join(dirpath, fn)))
                except OSError:
                    pass
    return datetime.date.fromtimestamp(latest)


def unique_dest(directory, stem, ext):
    cand = directory / (stem + ext)
    k = 2
    while cand.exists():
        cand = directory / ("%s-%d%s" % (stem, k, ext))
        k += 1
    return cand


def git_note(info):
    g = info.get("git")
    if not g:
        return ""
    last = (g.get("last_commit") or "").split(" ")[0]
    return "位于 git 仓库 %s（%s%s）" % (os.path.basename(g["root"]), g.get("branch_and_tracking") or "?", "，最近提交 " + last if last else "")


def write_inbox(agent, text, dry_run):
    cmd = [sys.executable, "-B", os.path.join(os.path.dirname(os.path.abspath(__file__)), "brain_write.py"), "--agent", agent]
    if dry_run:
        cmd.append("--dry-run")
    r = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=60)
    try:
        payload = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        payload = {"status": "error", "error": "brain_write 无 JSON 输出", "stdout": r.stdout[-500:], "stderr": r.stderr[-500:]}
    payload["returncode"] = r.returncode
    return payload


def main():
    ap = argparse.ArgumentParser(description="把交付物存进 brain/artifacts 并登记")
    ap.add_argument("--agent", required=True, choices=bc.AGENTS)
    ap.add_argument("--project", required=True, help="项目 id 或 MAP 别名")
    ap.add_argument("--title", required=True, help="一句人话标题，以后按它找回")
    ap.add_argument("--note", default="", help="备注：版本差异、用途、与哪个旧版的关系")
    ap.add_argument("--session", default="", help="会话 id 前 8 位，写进 inbox 标题行")
    ap.add_argument("--link", default="", help="云文档或仓库 URL；给了就不复制文件")
    ap.add_argument("--dry-run", action="store_true", help="只校验、算 md5、查重，不复制不登记")
    ap.add_argument("paths", nargs="*")
    a = ap.parse_args()

    if bool(a.link) == bool(a.paths):
        fail(2, error="args", detail="文件路径与 --link 二选一，且至少给一个")
    title = bc.nfc(a.title).strip()
    if not title or len(title) > 80:
        fail(2, error="args", detail="--title 必填，且不超过 80 字")
    if bc.SECRET_RE.search(title) or bc.SECRET_RE.search(a.note) or (a.link and bc.SECRET_RE.search(a.link)):
        fail(3, error="secret", detail="标题、备注或链接里疑似含密钥或凭证；去掉后重试")

    root = bc.find_root()
    machine = bc.machine_id(root)
    today = datetime.date.today()
    pid = bc.canonical_project(root, a.project)
    if not pid:
        fail(2, error="project", detail="项目「%s」不是合法 id：用小写字母、数字、连字符，或 MAP 里的别名" % a.project)
    warnings = brain_write.project_id_warnings(pid, "项目：" + pid + ("" if pid in bc.known_projects(root) else "（新）"),
                                               bc.known_projects(root), bc.aliases(root))
    if pid not in bc.known_projects(root):
        warnings.append("项目「%s」尚未登记，会按新项目写入；确认不是已有项目的别名再去掉 --dry-run" % pid)

    rows = index_rows(root)
    art_dir = root / "artifacts"
    source = "%s/%s" % (machine, a.agent)
    plan = []  # 每个待入库对象

    if a.link:
        url = a.link.strip()
        dup = [r for r in rows if r[5] == url]
        if dup:
            print(json.dumps({"status": "duplicate", "ids": [dup[0][0]], "detail": "该链接已登记为 %s（%s）" % (dup[0][0], dup[0][3]), "warnings": warnings}, ensure_ascii=False))
            return
        plan.append({"kind": "链接", "src": None, "url": url, "date": today, "md5": "", "size": 0, "note": a.note})
    else:
        for raw in a.paths:
            src = pathlib.Path(os.path.abspath(os.path.expanduser(raw)))
            if not src.exists():
                fail(2, error="missing", detail="路径不存在：%s" % src)
            try:
                src.relative_to(art_dir)
                fail(2, error="inside", detail="%s 已在产物库内，不必再存" % src)
            except ValueError:
                pass
            info = brain_verify.inspect(str(src))
            item = {"src": src, "url": "", "date": produced_date(src), "note": a.note, "git": git_note(info)}
            if src.is_dir():
                tmpdir = tempfile.mkdtemp(prefix="brain-store-")
                archive = shutil.make_archive(os.path.join(tmpdir, slug(src.name)), "zip", root_dir=str(src))
                item.update(kind="目录", payload=pathlib.Path(archive), ext=".zip", scanned=False)
            else:
                item.update(kind="文件", payload=src, ext=src.suffix.lower())
                bad, scanned = text_secret_lines(src, src.stat().st_size)
                item["scanned"] = scanned
                if bad:
                    fail(3, error="secret", path=str(src), lines=bad[:20], detail="文件里这些行疑似含密钥或凭证，未入库；清理后重试")
            item["size"] = item["payload"].stat().st_size
            item["md5"] = md5_of(item["payload"])
            dup = [r for r in rows if r[6].startswith("md5 " + item["md5"][:12])]
            if dup:
                item["dup"] = dup[0]
            if item["size"] > SIZE_WARN:
                warnings.append("%s 有 %s，iCloud 同步会慢；确认要存再继续" % (src.name, human(item["size"])))
            if not item["scanned"]:
                warnings.append("%s 按二进制处理，未扫描密钥" % src.name)
            plan.append(item)

    dups = [p for p in plan if p.get("dup")]
    todo = [p for p in plan if not p.get("dup")]
    if a.dry_run:
        print(json.dumps({"status": "dry-run", "project": pid, "would_store": [
            {"src": str(p["src"] or p["url"]), "kind": p["kind"], "md5": p["md5"][:12], "size": p["size"], "date": p["date"].isoformat()} for p in todo],
            "duplicates": [{"src": str(p["src"]), "existing_id": p["dup"][0], "existing_title": p["dup"][3]} for p in dups],
            "warnings": warnings}, ensure_ascii=False))
        return
    if not todo:
        print(json.dumps({"status": "duplicate", "ids": [p["dup"][0] for p in dups],
                          "detail": "全部已在库中：" + "；".join("%s（%s）" % (p["dup"][0], p["dup"][3]) for p in dups), "warnings": warnings}, ensure_ascii=False))
        return

    # 先用 dry-run 校验 inbox 条目能写（项目 id、来源、时间），再动文件。
    now = bc.now().strftime(bc.TIME_FMT)
    header = "## %s · 手动 | 项目：%s%s | 来源：%s%s" % (now, pid, "" if pid in bc.known_projects(root) else "（新）· " + title, source, (" | 会话：" + a.session) if a.session else "")
    probe = write_inbox(a.agent, header + "\n- 产物：[校验] 占位\n", dry_run=True)
    if probe.get("status") != "dry-run":
        fail(2, error="inbox", detail=probe)

    stored, entry_lines = [], []
    with bc.FileLock("artifacts-%s" % machine, fallback_dir=art_dir) as lock:
        if lock.warning:
            warnings.append(lock.warning)
        rows = index_rows(root)
        ipath = index_path(root)
        text = bc.read_text(ipath) if ipath.is_file() else INDEX_HEAD % today.isoformat()
        new_rows = []
        for p in todo:
            aid = next_id(rows + new_rows, today)
            if p["kind"] == "链接":
                pointer, check, origin = p["url"], "—", "—"
            else:
                pdir = art_dir / pid
                pdir.mkdir(parents=True, exist_ok=True)
                dest = unique_dest(pdir, "%s-%s" % (p["date"].isoformat(), slug(title)), p["ext"])
                tmp = dest.with_name(".%s.tmp-%d" % (dest.name, os.getpid()))
                shutil.copyfile(str(p["payload"]), str(tmp))
                if md5_of(tmp) != p["md5"]:
                    tmp.unlink(missing_ok=True)
                    fail(4, error="copy", detail="复制后 md5 不一致：%s" % p["src"])
                os.replace(str(tmp), str(dest))
                if md5_of(dest) != p["md5"]:
                    fail(4, error="readback", detail="回读 md5 不一致：%s" % dest)
                pointer = dest.relative_to(root).as_posix()
                check = "md5 %s · %s" % (p["md5"][:12], human(p["size"]))
                origin = "%s:%s" % (machine, p["src"])
            note = "；".join(x for x in (p["note"], p.get("git", "")) if x)
            row = [aid, p["date"].isoformat(), pid, title, p["kind"], pointer, check, origin, source, note]
            new_rows.append(row)
            stored.append({"id": aid, "kind": p["kind"], "pointer": pointer, "abs_path": str(root / pointer) if p["kind"] != "链接" else pointer,
                           "md5": p["md5"], "size": p["size"], "date": p["date"].isoformat()})
            if p["kind"] == "链接":
                entry_lines.append("- 产物：[链接] %s | %s（%s；brain_store 登记）" % (title, pointer, aid))
            else:
                entry_lines.append("- 产物：[%s] %s | %s | %s | 原位置 %s（%s；brain_store 复制并回读 md5 核实）" % (p["kind"], title, pointer, check, origin, aid))
        text = re.sub(r"^updated: .*$", "updated: %s" % today.isoformat(), text, count=1, flags=re.M)
        text = text.rstrip("\n") + "\n" + "\n".join("| " + " | ".join(cell(c) for c in r) + " |" for r in new_rows) + "\n"
        bc.atomic_write(ipath, text)
        back = bc.read_text(ipath)
        for r in new_rows:
            if ("| " + r[0] + " |") not in back:
                fail(4, error="index-readback", detail="INDEX 回读缺少 %s" % r[0])

    body = "\n".join(entry_lines + ["- 来源等级：产物为工具实测（brain_store 复制、md5 回读）"])
    inbox = write_inbox(a.agent, header + "\n" + body + "\n", dry_run=False)
    if inbox.get("status") != "ok":
        warnings.append("产物已入库并登记，但 inbox 条目写入失败：%s" % json.dumps(inbox, ensure_ascii=False)[:300])
    print(json.dumps({"status": "ok", "project": pid, "ids": [s["id"] for s in stored], "stored": stored,
                      "duplicates": [{"src": str(p["src"]), "existing_id": p["dup"][0]} for p in dups],
                      "index": str(index_path(root)), "entry_header": header, "entry_lines": entry_lines,
                      "inbox": {k: inbox.get(k) for k in ("status", "path", "warnings")}, "warnings": warnings}, ensure_ascii=False))


if __name__ == "__main__":
    main()
