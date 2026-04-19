#!/usr/bin/env python
import argparse
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent
ROOT = TOOLS_DIR.parent
TARGET_DIR = SCRIPT_DIR / "listenai-play"
TARGET_SCRIPT = TARGET_DIR / "scripts" / "listenai_play.py"
DEFAULT_REMOTE = "git@github-zjashanda:zjashanda/listenai-play.git"
DEFAULT_LOCAL_CACHE = Path(r"C:\Users\Administrator\.codex\skill-git-repos\listenai-play")


def run_command(command: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def get_local_cache() -> Path:
    raw = os.environ.get("LISTENAI_PLAY_LOCAL_CACHE", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return DEFAULT_LOCAL_CACHE


def ensure_git_available() -> None:
    result = run_command(["git", "--version"])
    if result.returncode != 0:
        raise RuntimeError("git is not available in PATH")


def target_is_git_repo() -> bool:
    return (TARGET_DIR / ".git").exists()


def apply_local_compat_patches() -> None:
    if not TARGET_SCRIPT.is_file():
        return

    text = TARGET_SCRIPT.read_text(encoding="utf-8")
    original = text
    text = text.replace('    return "$vidPid:$token"', "    return ('{0}:{1}' -f $vidPid, $token)")
    text = text.replace('    return "${vidPid}:$token"', "    return ('{0}:{1}' -f $vidPid, $token)")
    if text != original:
        TARGET_SCRIPT.write_text(text, encoding="utf-8")


def list_dirty_files() -> list[str]:
    if not target_is_git_repo():
        return []
    status = run_command(["git", "status", "--porcelain"], cwd=TARGET_DIR)
    if status.returncode != 0:
        return []
    dirty = []
    for line in (status.stdout or "").splitlines():
        if len(line) < 4:
            continue
        dirty.append(line[3:].strip())
    return dirty


def clone_from(source: str, remote_url: str) -> None:
    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)
    TARGET_DIR.parent.mkdir(parents=True, exist_ok=True)
    result = run_command(["git", "clone", source, str(TARGET_DIR)])
    if result.returncode != 0:
        raise RuntimeError(
            f"git clone failed from {source}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    run_command(["git", "remote", "set-url", "origin", remote_url], cwd=TARGET_DIR)
    apply_local_compat_patches()


def clone_repo(remote_url: str) -> str:
    local_cache = get_local_cache()
    if local_cache.is_dir() and (local_cache / ".git").exists():
        clone_from(str(local_cache), remote_url)
        return f"cloned from local cache: {local_cache}"

    clone_from(remote_url, remote_url)
    return f"cloned from remote: {remote_url}"


def update_repo(remote_url: str) -> str:
    if not TARGET_DIR.exists():
        return clone_repo(remote_url)
    if not target_is_git_repo():
        raise RuntimeError(f"target exists but is not a git repo: {TARGET_DIR}")

    run_command(["git", "remote", "set-url", "origin", remote_url], cwd=TARGET_DIR)
    dirty_files = list_dirty_files()
    auto_patch_rel = str(TARGET_SCRIPT.relative_to(TARGET_DIR)).replace("\\", "/")
    stash_note = ""
    if dirty_files:
        normalized = [item.replace("\\", "/") for item in dirty_files]
        if normalized == [auto_patch_rel]:
            checkout = run_command(["git", "checkout", "--", auto_patch_rel], cwd=TARGET_DIR)
            if checkout.returncode != 0:
                raise RuntimeError(
                    f"git checkout failed before update\nSTDOUT:\n{checkout.stdout}\nSTDERR:\n{checkout.stderr}"
                )
        else:
            stash = run_command(
                ["git", "stash", "push", "-u", "-m", "trisolaris-auto-sync-backup"],
                cwd=TARGET_DIR,
            )
            if stash.returncode != 0:
                raise RuntimeError(
                    f"git stash failed before update\nSTDOUT:\n{stash.stdout}\nSTDERR:\n{stash.stderr}"
                )
            stash_note = " (local changes were stashed)"

    fetch = run_command(["git", "fetch", "origin"], cwd=TARGET_DIR)
    if fetch.returncode != 0:
        raise RuntimeError(
            f"git fetch failed\nSTDOUT:\n{fetch.stdout}\nSTDERR:\n{fetch.stderr}"
        )

    pull = run_command(["git", "pull", "--ff-only"], cwd=TARGET_DIR)
    if pull.returncode != 0:
        raise RuntimeError(
            f"git pull failed\nSTDOUT:\n{pull.stdout}\nSTDERR:\n{pull.stderr}"
        )
    apply_local_compat_patches()
    return f"updated from remote{stash_note}"


def resolve_listenai_play(update: bool = False, remote_url: str = DEFAULT_REMOTE) -> Path:
    ensure_git_available()

    if update:
        status = update_repo(remote_url)
        if not TARGET_SCRIPT.is_file():
            raise RuntimeError(f"listenai_play.py missing after update: {TARGET_SCRIPT}")
        return TARGET_SCRIPT

    if TARGET_SCRIPT.is_file():
        apply_local_compat_patches()
        return TARGET_SCRIPT

    clone_repo(remote_url)
    apply_local_compat_patches()
    if not TARGET_SCRIPT.is_file():
        raise RuntimeError(f"listenai_play.py missing after clone: {TARGET_SCRIPT}")
    return TARGET_SCRIPT


def repo_status() -> dict:
    status = {
        "target_dir": str(TARGET_DIR),
        "target_exists": TARGET_DIR.exists(),
        "target_is_git_repo": target_is_git_repo(),
        "target_script_exists": TARGET_SCRIPT.is_file(),
        "remote_url": "",
    }
    if target_is_git_repo():
        remote = run_command(["git", "remote", "get-url", "origin"], cwd=TARGET_DIR)
        if remote.returncode == 0:
            status["remote_url"] = remote.stdout.strip()
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the local tools/audio/listenai-play checkout.")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Pull the latest remote changes into tools/audio/listenai-play.",
    )
    parser.add_argument(
        "--remote-url",
        default=DEFAULT_REMOTE,
        help="Override the git remote URL for tools/audio/listenai-play.",
    )
    parser.add_argument("--status", action="store_true", help="Print the current local repository status.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.status:
        import json

        print(json.dumps(repo_status(), ensure_ascii=False, indent=2))
        return 0

    script_path = resolve_listenai_play(update=args.update, remote_url=args.remote_url)
    print(script_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
