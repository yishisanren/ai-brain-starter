#!/usr/bin/env python3
"""brain 公共函数（仅标准库，兼容 Python 3.9+；macOS / Linux / Windows）。

定位根目录、识别本机、解析 MAP / INDEX、条目格式、时间窗、密钥检测、会话摘要渲染、
同机写锁、原子写入、skill bundle hash。brain-load、brain-note、brain-find、brain-merge 四处副本内容必须一致。
"""
import datetime
import hashlib
import os
import pathlib
import re
import socket
import stat
import sys
import time
import unicodedata

VERSION = "1.0.0"


def real_home():
    """真实用户目录。有的终端会把 HOME 指到别处，POSIX 下改读 passwd。"""
    try:
        import pwd
        return pathlib.Path(pwd.getpwuid(os.getuid()).pw_dir)
    except Exception:
        return pathlib.Path.home()


HOME = real_home()
CFG_DIR = HOME / ".config" / "brain"
STATE_DIR = HOME / ".local" / "state" / "brain"
SKILLS_DEST = HOME / ".agents" / "skills"
AGENTS = ("claude-code", "codex", "hermes")
TIME_FMT = "%Y-%m-%d %H:%M"
PLACEHOLDERS = ("", "—", "-", "待填")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")

ROOT_CANDIDATES = [
    HOME / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "obsidian",
    HOME / "Documents" / "obsidian",
    HOME / "obsidian",
]

ENTRY_RE = re.compile(
    r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · (日结|手动) \| (.+?) \| 来源：(\S+?)(?: \| 会话：(\S+))?[ \t]*$",
    re.M,
)

SECRET_RE = re.compile(
    r"(?<![A-Za-z0-9])sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"
    r"|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
    r"|xox[abprs]-[A-Za-z0-9-]{20,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|Bearer\s+(?![$<{])[^\s'\"]{20,}"
    r"|\b[a-z]{2,12}\\?_(?=[A-Za-z0-9]*[A-Z])(?=[A-Za-z0-9]*[a-z])(?=[A-Za-z0-9]*[0-9])[A-Za-z0-9]{24,}"
    r"|(?i:\b(?:password|passwd|api[_-]?key|secret[_-]?key|client[_-]?secret|access[_-]?token|auth[_-]?token)\b"
    r"\s*[:=]\s*['\"]?(?![$<{%*]|os\.|process\.|env\b|none\b|null\b)[^\s'\"]{8,})"
    r"|(?:密码|口令)\s*[:：]\s*\S{6,}"
    r"|https?://[^\s/:@]+:[^\s/@]{3,}@[^\s/]+"
)

SYS_TAG_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
NOISE_PREFIXES = ("<local-command-stdout>", "<local-command-caveat>", "<local-command-stderr>")


def redact(text):
    return SECRET_RE.sub("[已脱敏]", text)


def secret_lines(text):
    return [i + 1 for i, line in enumerate(text.splitlines()) if SECRET_RE.search(line)]


def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = SYS_TAG_RE.sub("", text).strip()
    if not text or text.startswith(NOISE_PREFIXES):
        return ""
    return text


def read_text(path):
    return pathlib.Path(path).read_text(encoding="utf-8-sig", errors="replace")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def now():
    return datetime.datetime.now().replace(second=0, microsecond=0)


def parse_time(s):
    return datetime.datetime.strptime(s.strip(), TIME_FMT)


def find_root():
    env = os.environ.get("BRAIN_ROOT", "").strip()
    if env:
        p = pathlib.Path(env).expanduser()
        if (p / "MAP.md").is_file():
            return p
        raise SystemExit("BRAIN_ROOT=%s 下没有 MAP.md" % p)
    cfg = CFG_DIR / "root"
    if cfg.is_file():
        p = pathlib.Path(read_text(cfg).strip()).expanduser()
        if (p / "MAP.md").is_file():
            return p
    for base in ROOT_CANDIDATES:
        p = base / "4-助理" / "brain"
        if (p / "MAP.md").is_file():
            return p
    raise SystemExit("找不到 brain 根目录：设置环境变量 BRAIN_ROOT，或把根目录路径写进 %s" % (CFG_DIR / "root"))


def md_sections(text):
    """{二级标题: [表格数据行]}；每张表跳过表头与分隔行。二级标题之前的表归在 "" 下。"""
    out = {}
    title = ""
    in_table = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            title = line[3:].strip()
            out.setdefault(title, [])
            in_table = False
            continue
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not in_table:
            in_table = True
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        out.setdefault(title, []).append(cells)
    return out


def clean(cell):
    return cell.strip().strip("`").strip()


def section_rows(sections, prefix):
    for title, rows in sections.items():
        if title.startswith(prefix):
            return [[clean(c) for c in r] for r in rows if any(clean(c) not in PLACEHOLDERS for c in r)]
    return []


def section_text(text, prefix):
    buf = None
    for line in text.splitlines():
        if line.startswith("## "):
            if buf is not None:
                break
            if line[3:].strip().startswith(prefix):
                buf = []
            continue
        if buf is not None:
            buf.append(line)
    return "\n".join(buf).strip() if buf else ""


def load_map(root):
    return md_sections(read_text(root / "MAP.md"))


def machine_id(root):
    env = os.environ.get("BRAIN_MACHINE", "").strip()
    if env:
        return env
    cfg = CFG_DIR / "machine"
    if cfg.is_file():
        value = read_text(cfg).strip()
        if value:
            return value
    host = socket.gethostname().lower()
    for row in section_rows(load_map(root), "机器"):
        if len(row) >= 2 and row[1] not in PLACEHOLDERS and row[1].lower() in host:
            return row[0]
    raise SystemExit("MAP.md「机器」表里没有匹配 hostname=%s 的行；补一行，或把机器名写进 %s" % (host, CFG_DIR / "machine"))


def norm_path(p):
    s = nfc(os.path.normpath(os.path.expanduser(str(p))))
    if sys.platform in ("darwin", "win32"):
        s = s.casefold()
    return s


def project_for_cwd(root, machine, cwd):
    if not cwd:
        return None
    target = norm_path(cwd)
    best = None
    for row in section_rows(load_map(root), "目录"):
        if len(row) < 3 or row[0] != machine or row[1] in PLACEHOLDERS:
            continue
        base = norm_path(row[1]).rstrip("/\\")
        if target == base or target.startswith(base + os.sep) or target.startswith(base + "/"):
            if best is None or len(base) > best[0]:
                best = (len(base), row[2])
    return best[1] if best else None


def aliases(root):
    out = {}
    for row in section_rows(load_map(root), "别名"):
        if len(row) >= 2:
            out[row[0].casefold()] = row[1]
    return out


def index_rows(root):
    p = root / "projects" / "INDEX.md"
    return section_rows(md_sections(read_text(p)), "项目") if p.is_file() else []


def known_projects(root):
    ids = {row[0] for row in index_rows(root) if row}
    pdir = root / "projects"
    if pdir.is_dir():
        ids.update(p.name for p in pdir.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))
    return ids


def project_key(field):
    """「项目：foo（新）· 一句话」→ foo。"""
    s = field.strip()
    if s.startswith("项目："):
        s = s[3:]
    for sep in ("（新）", "(新)", " · ", "·"):
        s = s.split(sep)[0]
    return s.strip()


def canonical_project(root, name):
    key = project_key(name)
    if not key:
        return None
    if key in known_projects(root):
        return key
    al = aliases(root)
    if key.casefold() in al:
        return al[key.casefold()]
    return key if SLUG_RE.match(key) else None


def resolve_project(root, machine, name=None, cwd=None):
    """返回 (项目 id 或 None, 依据)。"""
    if name:
        key = project_key(name)
        if key in known_projects(root):
            return key, "用户点名"
        al = aliases(root)
        if key.casefold() in al:
            return al[key.casefold()], "别名「%s」" % key
        if SLUG_RE.match(key):
            return key, "用户点名（新项目）"
        return None, "用户点名「%s」不是合法 id，需要转成小写字母、数字、连字符" % key
    pid = project_for_cwd(root, machine, cwd or os.getcwd())
    if pid:
        return pid, "目录映射"
    return None, "未绑定"


def split_entries(text):
    heads = list(ENTRY_RE.finditer(text))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        out.append({
            "time": m.group(1), "kind": m.group(2), "project_field": m.group(3).strip(),
            "source": m.group(4), "session": m.group(5), "header": m.group(0).rstrip(),
            "body": text[m.end():end].strip("\n"), "raw": text[m.start():end].rstrip(),
        })
    return out


def last_daily_time(root, machine, agent):
    d = root / "inbox" / machine / agent
    if not d.is_dir():
        return None
    for f in sorted(d.glob("*.md"), reverse=True)[:14]:
        times = [e["time"] for e in split_entries(read_text(f)) if e["kind"] == "日结"]
        if times:
            return parse_time(max(times))
    return None


def resolve_since(root, machine, agent, since_arg="auto"):
    if since_arg and since_arg != "auto":
        return parse_time(since_arg), "指定"
    t = last_daily_time(root, machine, agent)
    if t:
        return t, "上次日结"
    y = now() - datetime.timedelta(days=1)
    return y.replace(hour=19, minute=0), "默认：昨天 19:00"


def render_sessions(root, machine, sessions, cap, trim):
    lines = []
    for s in sessions:
        msgs = s["msgs"]
        project = s.get("project") or project_for_cwd(root, machine, s.get("cwd")) or "未映射"
        extra = ""
        if s.get("source"):
            extra += " · 来源 %s" % s["source"]
        if s.get("title"):
            extra += " · 标题 %s" % redact(str(s["title"]))[:60]
        lines.append("")
        lines.append("## 会话 %s · %s → %s · %d 条 · 目录 %s · 映射项目 %s%s" % (
            str(s.get("id"))[:12], msgs[0][0].strftime("%m-%d %H:%M"), msgs[-1][0].strftime("%m-%d %H:%M"),
            len(msgs), s.get("cwd") or "未知", project, extra))
        shown, omitted = msgs, 0
        if trim and len(msgs) > 16:
            omitted = len(msgs) - 16
            shown = msgs[:4] + msgs[-12:]
        for i, (ts, who, text) in enumerate(shown):
            if omitted and i == 4:
                lines.append("（中间省略 %d 条）" % omitted)
            t = re.sub(r"\n{3,}", "\n\n", redact(text))
            if len(t) > cap:
                t = t[:cap] + "…（截断，原长 %d 字）" % len(text)
            lines.append("%s %s：%s" % (who, ts.strftime("%H:%M"), t))
    return "\n".join(lines)


def fit_render(root, machine, sessions, max_chars, per_msg):
    body, cap = "", per_msg
    for cap in sorted({per_msg, max(300, per_msg // 2), 300}, reverse=True):
        body = render_sessions(root, machine, sessions, cap, cap == 300)
        if len(body) <= max_chars:
            return body, cap
    return body[:max_chars] + "\n…（摘要超过 %d 字上限，已截断）" % max_chars, cap


class FileLock(object):
    """同机互斥锁。优先放 vault 之外；沙箱里不可写时退到目标目录的隐藏锁文件；都不可写则不加锁并给出 warning。"""

    def __init__(self, name, timeout=30, stale=180, fallback_dir=None):
        self.name = re.sub(r"[^A-Za-z0-9_.-]", "_", name) + ".lock"
        self.timeout, self.stale = timeout, stale
        self.primary = STATE_DIR / "locks"
        self.candidates = [self.primary] + ([pathlib.Path(fallback_dir)] if fallback_dir else [])
        self.path = None
        self.warning = ""

    def _acquire(self, directory):
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (self.name if directory == self.primary else "." + self.name)
        deadline = time.time() + self.timeout
        while True:
            try:
                fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return path
            except FileExistsError:
                try:
                    if time.time() - path.stat().st_mtime > self.stale:
                        path.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.time() > deadline:
                    raise SystemExit("等待写锁超时：%s" % path)
                time.sleep(0.3)

    def __enter__(self):
        for directory in self.candidates:
            try:
                self.path = self._acquire(directory)
                if directory != self.primary:
                    self.warning = "锁目录 %s 不可写，改用 %s" % (self.primary, self.path)
                return self
            except OSError:
                continue
        self.warning = "所有锁目录都不可写，本次未加锁"
        return self

    def __exit__(self, *exc):
        if self.path is not None:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass


def atomic_write(path, content):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(".%s.tmp-%d" % (path.name, os.getpid()))
    with open(str(tmp), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(str(tmp), str(path))


_IGN_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv", ".mypy_cache", ".ruff_cache", ".tox", ".idea"}
_IGN_FILE_RE = re.compile(r"^\.DS_Store$|^\._|\.tmp$|\.swp$|\.swo$|\.bak$|\.orig$|\.part$|\.crdownload$|~$|^\.~|^~\$")


def bundle_sha256_v2(directory):
    """shared-skill-bundle-v2：与 ~/.local/state/shared-skills/registry.json 的定义一致。"""
    d = pathlib.Path(directory)
    items = []
    for dirpath, dirnames, filenames in os.walk(str(d), followlinks=False):
        keep = []
        for dn in dirnames:
            full = pathlib.Path(dirpath) / dn
            if dn in _IGN_DIRS:
                continue
            if full.is_symlink():
                items.append((full.relative_to(d).as_posix(), "l", os.readlink(str(full))))
                continue
            keep.append(dn)
        dirnames[:] = keep
        for fn in filenames:
            if _IGN_FILE_RE.search(fn):
                continue
            full = pathlib.Path(dirpath) / fn
            rel = full.relative_to(d).as_posix()
            if full.is_symlink():
                items.append((rel, "l", os.readlink(str(full))))
                continue
            mode = full.stat().st_mode
            exe = "755" if mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) else "644"
            items.append((rel, "f", hashlib.sha256(full.read_bytes()).hexdigest() + ":" + exe))
    h = hashlib.sha256()
    for rel, kind, payload in sorted(items, key=lambda x: x[0]):
        h.update(("%s\0%s\0%s\n" % (rel, kind, payload)).encode("utf-8"))
    return h.hexdigest()
