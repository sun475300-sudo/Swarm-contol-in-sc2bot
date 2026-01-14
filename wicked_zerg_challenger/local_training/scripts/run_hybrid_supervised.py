#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid Supervised Runner

Purpose:
- Loop over epochs to generate/update replay selection manifests using HybridTrainer
- Keep responsibilities separated: selection (this runner + HybridTrainer) vs actual training

Notes:
- This runner does NOT implement a full supervised training pipeline from replays.
- It prepares/refreshes the manifest per epoch so a downstream trainer can consume it.
- If you later add a replay-based trainer, you can call it in the marked section below.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


def run_epochs(
    epochs: int,
    max_files: Optional[int],
    pro_only: bool,
    zvp_priority: bool,
    replay_dir: Optional[str],
    output_dir: Path,
) -> None:
    # Import locally to avoid import-time side effects if not needed
    from hybrid_learning import HybridTrainer

    output_dir.mkdir(parents=True, exist_ok=True)

    trainer = HybridTrainer(replay_dir=replay_dir)

    # IMPROVED: Validate replay directory and handle missing manifest
    latest_manifest = output_dir / "hybrid_learning_manifest.json"
    if not latest_manifest.exists():
        print(f"[INFO] No existing manifest found at {latest_manifest}")
        print(f"[INFO] Will create new manifest from replay directory: {replay_dir}")

    for epoch in range(1, epochs + 1):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        epoch_manifest = output_dir / f"hybrid_learning_manifest_epoch{epoch:02d}_{ts}.json"
        latest_manifest = output_dir / "hybrid_learning_manifest.json"

        count = trainer.train_supervised(
            max_files=max_files,
            pro_only=pro_only,
            zvp_priority=zvp_priority,
            output_path=epoch_manifest,
        )

        # IMPROVED: Enhanced manifest handling with validation
        # Keep a stable pointer for downstream tools
        try:
            if not epoch_manifest.exists():
                print(f"[WARNING] Epoch manifest not created: {epoch_manifest}")
                continue

            manifest_content = epoch_manifest.read_text(encoding="utf-8")
            if not manifest_content.strip():
                print(f"[WARNING] Epoch manifest is empty: {epoch_manifest}")
                continue

            # Validate JSON before writing
            try:
                json.loads(manifest_content)  # Validate JSON structure
            except json.JSONDecodeError as e:
                print(f"[ERROR] Epoch manifest contains invalid JSON: {e}")
                continue

            if latest_manifest.exists():
                latest_manifest.unlink()
            latest_manifest.write_text(manifest_content, encoding="utf-8")
        except Exception as e:
            # Best effort; do not fail the loop due to file replacement issues
            print(f"[WARNING] Failed to update latest manifest: {e}")
            pass

        print(f"[EPOCH {epoch}/{epochs}] Selected {count} replays -> {epoch_manifest}")
        print(f"[EPOCH {epoch}/{epochs}] Latest manifest refreshed -> {latest_manifest}")

        # Placeholder for actual supervised training step
        # TODO: Integrate your replay-based trainer here, e.g.:
        # train_from_manifest(latest_manifest)
        # For now, we only prepare the manifest per epoch.


def main() -> None:
    parser = argparse.ArgumentParser(description="Run hybrid supervised selection for multiple epochs")
    parser.add_argument("--epochs", type=int, default=1, help="Number of epochs to repeat selection")
    parser.add_argument("--max-files", type=int, default=0, help="Limit number of selected replays (0 = no limit)")
    parser.add_argument("--pro-only", action="store_true", help="Filter to known pro-player replays")
    parser.add_argument("--zvp-priority", action="store_true", help="Filter to ZvP/PvZ only")
    parser.add_argument(
        "--replay-dir",
        default=None,
        help="Replay directory (default: auto-detected from common locations)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path("data")),
        help="Directory to write manifests (default: ./data)",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    max_files = args.max_files if args.max_files > 0 else None

    run_epochs(
        epochs=max(1, args.epochs),
        max_files=max_files,
        pro_only=args.pro_only,
        zvp_priority=args.zvp_priority,
        replay_dir=args.replay_dir,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
