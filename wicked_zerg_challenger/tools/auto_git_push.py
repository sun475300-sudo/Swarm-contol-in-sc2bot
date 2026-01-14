import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERVAL = int(os.getenv("AUTO_PUSH_INTERVAL_SEC", "300"))  # default 5 minutes
REMOTE = os.getenv("AUTO_PUSH_REMOTE", "origin")
LOG_FILE = ROOT / "tools" / "auto_git_push.log"


def run_git(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.Popen(
        ["git", *args], cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    out, err = proc.communicate()
    return proc.returncode, out, err


def has_changes() -> bool:
    code, out, err = run_git(["status", "--porcelain"])
    if code != 0:
        log(f"git status failed: {err.strip()}")
        return False
    return bool(out.strip())


def get_branch() -> str | None:
    code, out, err = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if code == 0:
        return out.strip()
    log(f"git branch detect failed: {err.strip()}")
    return None


def push_with_upstream(branch: str) -> bool:
    code, out, err = run_git(["push", "-u", REMOTE, branch])
    if code == 0:
        return True
    log(f"git push -u failed: {err.strip()}")
    return False


def push() -> bool:
    code, out, err = run_git(["push"])
    if code == 0:
        return True
    if "set the remote as upstream" in err.lower() or "no upstream" in err.lower():
        br = get_branch()
        if br:
            return push_with_upstream(br)
    log(f"git push failed: {err.strip()}")
    return False


def get_changed_files_summary() -> str:
    """Get a summary of changed files for commit message."""
    code, out, err = run_git(["status", "--porcelain"])
    if code != 0 or not out.strip():
        return "updates"

    lines = [l for l in out.strip().split("\n") if l.strip()]
    added = modified = deleted = 0
    changed_files = []

    for line in lines:
        status = line[:2].strip()
        file = line[3:].split("->")[-1].strip() if "->" in line else line[3:].strip()

        if status in ["A", "??", "AM"]:
            added += 1
        elif status in ["M", "MM"]:
            modified += 1
        elif status in ["D"]:
            deleted += 1

        # Get main category (first folder or filename)
        if "/" in file:
            category = file.split("/")[0]
        else:
            category = file.split(".")[0] if "." in file else file

        if category not in changed_files and len(changed_files) < 3:
            changed_files.append(category)

    # Build summary
    parts = []
    if added > 0:
        parts.append(f"+{added}")
    if modified > 0:
        parts.append(f"~{modified}")
    if deleted > 0:
        parts.append(f"-{deleted}")

    count_summary = ",".join(parts) if parts else "updates"

    if changed_files:
        files_summary = ",".join(changed_files)
        return f"{count_summary} {files_summary}"
    return count_summary


def commit_all() -> bool:
    # stage
    code, out, err = run_git(["add", "-A"])
    if code != 0:
        log(f"git add failed: {err.strip()}")
        return False

    # Generate smart commit message
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg_prefix = os.getenv("AUTO_PUSH_MESSAGE_PREFIX", "chore")

    # Get summary of changes
    summary = get_changed_files_summary()

    # Format: "chore: auto-sync (+2,~5) wicked_zerg_bot_pro,config [2026-01-10 15:30:00]"
    msg = f"{msg_prefix}: auto-sync ({summary}) [{ts}]"

    code, out, err = run_git(["commit", "-m", msg])
    if code != 0:
        # likely nothing to commit
        if "nothing to commit" in (out + err).lower():
            return True
        log(f"git commit failed: {err.strip() or out.strip()}")
        return False
    log(f"committed: {msg}")
    return True


def log(message: str) -> None:
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n"
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    print(line, end="")


def main() -> int:
    log(f"auto_git_push started. interval={INTERVAL}s, remote={REMOTE}, root={ROOT}")
    # Probe git
    br = get_branch()
    if not br:
        log("No git branch detected. Exiting.")
        return 1
    log(f"current branch: {br}")

    while True:
        try:
            if has_changes():
                if commit_all():
                    if push():
                        log("pushed successfully")
                    else:
                        log("push failed")
                else:
                    log("commit failed")
            else:
                log("no changes; skipping")
        except Exception as e:
            log(f"unexpected error: {e}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
