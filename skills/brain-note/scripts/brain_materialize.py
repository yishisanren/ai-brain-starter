#!/usr/bin/env python3
"""brain_materialize：把 brain/skills/<name>/ 物化到 ~/.agents/skills/<name>/。

- 只管理自己物化过的技能（台账 ~/.local/state/brain/materialized.json）；同名的非 brain 技能不覆盖。
- skill.lock.json 的 targets.machines 限定目标机器；本机不在列表内则不安装，已装的移除。
- 按 bundle hash（shared-skill-bundle-v2）判断是否更新；暂存目录复制并校验后原子切换。
- Claude Code 在 ~/.claude/skills/ 建相对软链，失败时复制；Codex、Hermes 直接读 ~/.agents/skills。
用法：python3 -B brain_materialize.py [--dry-run]
"""
import argparse
import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_common as bc  # noqa: E402

IGNORE = shutil.ignore_patterns(".DS_Store", "._*", "__pycache__", "*.pyc", ".git")


def wanted_skills(src_root, machine):
    out = {}
    if not src_root.is_dir():
        return out
    for p in sorted(src_root.iterdir()):
        if not p.is_dir() or p.name.startswith(("_", ".")) or not (p / "SKILL.md").is_file():
            continue
        machines = None
        lock = p / "skill.lock.json"
        if lock.is_file():
            try:
                machines = (json.loads(bc.read_text(lock)).get("targets") or {}).get("machines")
            except ValueError:
                machines = None
        if machines and machine not in machines:
            continue
        out[p.name] = p
    return out


def main():
    ap = argparse.ArgumentParser(description="物化 brain 公共技能")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="本机副本被改过时也覆盖（先把本机副本备份到 ~/.local/state/brain/backups/）")
    a = ap.parse_args()
    root = bc.find_root()
    machine = bc.machine_id(root)
    dest = bc.SKILLS_DEST
    dest.mkdir(parents=True, exist_ok=True)
    bc.STATE_DIR.mkdir(parents=True, exist_ok=True)
    ledger_path = bc.STATE_DIR / "materialized.json"
    ledger = json.loads(bc.read_text(ledger_path)) if ledger_path.is_file() else {}
    wanted = wanted_skills(root / "skills", machine)
    report = []
    drift = []
    with bc.FileLock("materialize-%s" % machine, timeout=120):
        for name in sorted(wanted, key=lambda n: (n == "brain-note", n)):
            src, dst = wanted[name], dest / name
            h = bc.bundle_sha256_v2(src)
            if (dst.exists() or dst.is_symlink()) and name not in ledger:
                report.append("SKIP %s：本机已有非 brain 物化的同名技能，未覆盖" % name)
                continue
            local = bc.bundle_sha256_v2(dst) if dst.is_dir() else None
            if local == h:
                if ledger.get(name) != h and not a.dry_run:
                    ledger[name] = h
                    report.append("LEDGER %s %s（本机副本已与 vault 一致）" % (name, h[:8]))
                continue
            if local is not None and local != ledger.get(name):
                # 本机副本在上次物化后被直接改过：vault 才是源，不能静默覆盖，也不能让改动丢失。
                if a.force and not a.dry_run:
                    bk = bc.STATE_DIR / "backups" / ("%s-drift-%s" % (bc.now().strftime("%Y%m%d-%H%M"), name))
                    shutil.copytree(str(dst), str(bk), ignore=IGNORE)
                    report.append("FORCE %s：本机副本已备份到 %s，改用 vault 版本" % (name, bk))
                else:
                    drift.append(name)
                    report.append("DRIFT %s：本机副本被直接改过（%s≠台账 %s），未覆盖。把改动合回 vault 的 skills/%s/ 再同步；确认丢弃就加 --force"
                                  % (name, local[:8], (ledger.get(name) or "无")[:8], name))
                    continue
            if a.dry_run:
                report.append("WOULD-UPDATE %s %s" % (name, h[:8]))
                continue
            tmp = pathlib.Path(tempfile.mkdtemp(dir=str(dest), prefix=".%s.tmp-" % name))
            shutil.rmtree(str(tmp))
            shutil.copytree(str(src), str(tmp), ignore=IGNORE)
            got = bc.bundle_sha256_v2(tmp)
            if got != h:
                shutil.rmtree(str(tmp), ignore_errors=True)
                report.append("FAIL %s：复制后 hash 不一致（%s≠%s）" % (name, got[:8], h[:8]))
                continue
            old = None
            if dst.exists():
                old = dest / (".%s.old-%d" % (name, os.getpid()))
                os.replace(str(dst), str(old))
            os.replace(str(tmp), str(dst))
            if old:
                shutil.rmtree(str(old), ignore_errors=True)
            ledger[name] = h
            report.append("UPDATE %s %s" % (name, h[:8]))
        for name in sorted(set(ledger) - set(wanted)):
            if a.dry_run:
                report.append("WOULD-REMOVE %s" % name)
                continue
            shutil.rmtree(str(dest / name), ignore_errors=True)
            link = bc.HOME / ".claude" / "skills" / name
            if link.is_symlink():
                link.unlink()
            del ledger[name]
            report.append("REMOVE %s" % name)
        if not a.dry_run:
            bc.atomic_write(ledger_path, json.dumps(ledger, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
            claude = bc.HOME / ".claude" / "skills"
            if claude.is_dir():
                for name in sorted(ledger):
                    link = claude / name
                    if link.is_symlink() or link.exists():
                        continue
                    try:
                        os.symlink(os.path.join("..", "..", ".agents", "skills", name), str(link))
                        report.append("LINK claude %s" % name)
                    except OSError:
                        shutil.copytree(str(dest / name), str(link), ignore=IGNORE)
                        report.append("COPY-FOR-CLAUDE %s" % name)
    print("\n".join(report) if report else "brain skills: no change（%d 个已是最新）" % len(ledger))
    if drift:
        print("WARNING: %d 个技能的本机副本与 vault 不一致，已跳过：%s" % (len(drift), ", ".join(drift)))
        sys.exit(5)


if __name__ == "__main__":
    main()
