import argparse
import ast
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "logs",
    "models",
    "replays",
    "backups",
    "AI_Arena_Deploy",
    "AI_Arena_Updates",
    "aiarena_submission",
    "data",  # runtime data
}


def should_exclude(path: Path) -> bool:
    parts = set(path.parts)
    return any(d in parts for d in EXCLUDE_DIRS)


def walk_py_files(base: Path):
    for root, dirs, files in os.walk(base):
        root_path = Path(root)
        # prune excluded dirs
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if not f.endswith(".py"):
                continue
            p = root_path / f
            if should_exclude(p):
                continue
            yield p


class ImportUsageVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imported: set[str] = set()
        self.used: set[str] = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imported.add(alias.asname or alias.name.split(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            self.imported.add(alias.asname or alias.name)

    def visit_Name(self, node: ast.Name):
        self.used.add(node.id)

    def visit_Attribute(self, node: ast.Attribute):
        # record the base identifier of attribute chains (e.g., module.attr)
        v = node
        while isinstance(v, ast.Attribute):
            v = v.value
        if isinstance(v, ast.Name):
            self.used.add(v.id)
        self.generic_visit(node)


def analyze_file(path: Path):
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src)
    except Exception:
        return None
    vis = ImportUsageVisitor()
    vis.visit(tree)
    unused = sorted([n for n in vis.imported if n not in vis.used])
    return {
        "file": path,
        "unused": unused,
        "unused_count": len(unused),
        "imported_count": len(vis.imported),
    }


def main():
    ap = argparse.ArgumentParser(description="Scan for potentially unused imports across Python files")
    ap.add_argument("--top", type=int, default=10, help="Show top N files by unused import count")
    args = ap.parse_args()

    results = []
    for p in walk_py_files(ROOT):
        r = analyze_file(p)
        if r is not None and r["unused_count"] > 0:
            results.append(r)

    results.sort(key=lambda r: r["unused_count"], reverse=True)
    print(f"Files with unused imports: {len(results)}")
    for r in results[: args.top]:
        rel = r["file"].relative_to(ROOT)
        print(f"- {rel}: {r['unused_count']} unused -> {', '.join(r['unused'])}")


if __name__ == "__main__":
    main()
