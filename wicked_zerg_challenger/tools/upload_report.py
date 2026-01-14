import argparse
from pathlib import Path
from datetime import datetime


def timestamped_name(base: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = base.stem
    return base.with_name(f"{stem}_{ts}{base.suffix}")


def upload_report(src_path: str, dst_dir: str, add_header: bool = True):
    src = Path(src_path)
    if not src.exists():
        raise FileNotFoundError(f"Source report not found: {src}")

    dst_root = Path(dst_dir)
    dst_root.mkdir(parents=True, exist_ok=True)

    dst = timestamped_name(dst_root / src.name)

    content = src.read_text(encoding="utf-8", errors="ignore")
    if add_header:
        # Prepend a timestamp header if Markdown or text
        header = f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        if src.suffix.lower() in {".md", ".txt"}:
            content = header + content

    dst.write_text(content, encoding="utf-8")
    print(f"[UPLOAD] Report copied to {dst}")


def main():
    parser = argparse.ArgumentParser(description="Upload report with timestamped filename")
    parser.add_argument("src", help="Path to the source report file (e.g., REPORT.md)")
    parser.add_argument("--dst-dir", default="reports", help="Destination directory for timestamped reports")
    parser.add_argument("--no-header", action="store_true", help="Do not prepend timestamp header to content")
    args = parser.parse_args()

    upload_report(args.src, args.dst_dir, add_header=not args.no_header)


if __name__ == "__main__":
    main()
