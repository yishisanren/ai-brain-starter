#!/usr/bin/env python3
"""brain_verify：写「产物」之前的只读核实。不联网，不修改任何文件。

用法：python3 -B brain_verify.py <路径> [<路径> ...]
每个路径输出一行 JSON：是否存在、类型、大小与修改时间；若位于 git 仓库内，再给出分支与本地远端引用的领先落后、未提交改动数、最近一次提交。
"""
import datetime
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True


def git(args, cwd):
    try:
        r = subprocess.run(["git", "-C", cwd] + args, capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL)
        return r.returncode, r.stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def inspect(raw):
    path = os.path.abspath(os.path.expanduser(raw))
    info = {"path": path, "exists": os.path.exists(path)}
    if not info["exists"]:
        return info
    info["type"] = "dir" if os.path.isdir(path) else "file"
    st = os.stat(path)
    info["mtime"] = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
    if info["type"] == "file":
        info["size"] = st.st_size
    base = path if info["type"] == "dir" else os.path.dirname(path)
    rc, top = git(["rev-parse", "--show-toplevel"], base)
    if rc != 0:
        info["git"] = None
        return info
    _, status = git(["status", "--porcelain=v1", "-b"], top)
    lines = status.splitlines()
    head = lines[0][3:] if lines and lines[0].startswith("## ") else ""
    _, last = git(["log", "-1", "--format=%h %ci %s"], top)
    info["git"] = {"root": top, "branch_and_tracking": head, "uncommitted": max(0, len(lines) - 1),
                   "last_commit": last, "note": "领先落后按本地远端引用计算，未联网拉取"}
    return info


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法：brain_verify.py <路径> [<路径> ...]")
    for raw in sys.argv[1:]:
        print(json.dumps(inspect(raw), ensure_ascii=False))


if __name__ == "__main__":
    main()
