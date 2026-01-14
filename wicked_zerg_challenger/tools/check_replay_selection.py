import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPLAYS_DIRS = [ROOT / "replays", ROOT]
CONFIG = ROOT / "data" / "pro_players.json"


def load_pro_players():
    if not CONFIG.exists():
        return set()
    try:
        with CONFIG.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        names = cfg.get("players", [])
        return {name.lower() for name in names}
    except Exception:
        return set()


def list_replays():
    files = []
    for base in REPLAYS_DIRS:
        if not base.exists():
            continue
        for p in base.glob("*.SC2Replay"):
            files.append(p)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def is_pro_file(p: Path, pro_names: set[str]) -> bool:
    name = p.name.lower()
    return any(n in name for n in pro_names)


def select_files(files, pro_names, pro_only: bool, max_files: int | None):
    pro_files = [p for p in files if is_pro_file(p, pro_names)]
    non_pro_files = [p for p in files if p not in pro_files]
    selected = []
    if pro_only:
        selected = pro_files
    else:
        selected = pro_files + non_pro_files
    if max_files is not None:
        selected = selected[: max_files]
    return pro_files, non_pro_files, selected


def main():
    ap = argparse.ArgumentParser(description="Preview replay selection with pro-first policy")
    ap.add_argument("--pro-only", action="store_true", help="Select only pro replays")
    ap.add_argument("--max-files", type=int, default=None, help="Limit total selected files")
    args = ap.parse_args()

    pro_names = load_pro_players()
    files = list_replays()
    pro_files, non_pro_files, selected = select_files(files, pro_names, args.pro_only, args.max_files)

    print(f"Total replays: {len(files)}")
    print(f"Pro names loaded: {len(pro_names)}")
    print(f"Pro replays found: {len(pro_files)}")
    print(f"Non-pro replays found: {len(non_pro_files)}")
    print(f"Selected: {len(selected)} (pro-only={args.pro_only}, max={args.max_files})")

    for label, group in [("Selected", selected[:10])]:
        print(f"\n{label} (up to 10 shown):")
        for p in group:
            kind = "PRO" if p in pro_files else "REG"
            print(f"- [{kind}] {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
