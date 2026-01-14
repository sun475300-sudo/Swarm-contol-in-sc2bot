from pathlib import Path
import shutil


def remove_dir(path: Path) -> bool:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
        print(f"[CLEANUP] Removed {path}")
        return True
    else:
        print(f"[CLEANUP] Not found: {path}")
        return False


def main():
    root = Path(__file__).resolve().parent.parent
    aiarena = root / "aiarena_submission"
    deploy = root / "AI_Arena_Deploy"
    removed_any = False
    removed_any |= remove_dir(aiarena)
    removed_any |= remove_dir(deploy)
    if not removed_any:
        print("[CLEANUP] Nothing to remove; workspace already clean")


if __name__ == "__main__":
    main()
