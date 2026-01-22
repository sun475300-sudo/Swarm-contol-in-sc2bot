#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid supervised runner.

Prepares a replay manifest per epoch for downstream training.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from .hybrid_trainer import HybridTrainer
except ImportError:  # Fallback for script execution
    from hybrid_trainer import HybridTrainer  # type: ignore[no-redef]


def run_epochs(
    epochs: int,
    max_files: Optional[int],
    pro_only: bool,
    zvp_priority: bool,
    replay_dir: Optional[str],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    trainer = HybridTrainer(replay_dir=replay_dir)

    latest_manifest = output_dir / "hybrid_learning_manifest.json"
    if not latest_manifest.exists():
        print(f"[INFO] No existing manifest found at {latest_manifest}")

    for epoch in range(1, epochs + 1):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        epoch_manifest = (
            output_dir / f"hybrid_learning_manifest_epoch{epoch:02d}_{ts}.json"
        )
        latest_manifest = output_dir / "hybrid_learning_manifest.json"

        count = trainer.train_supervised(
            max_files=max_files,
            pro_only=pro_only,
            zvp_priority=zvp_priority,
            output_path=epoch_manifest,
        )

        try:
            manifest_content = epoch_manifest.read_text(encoding="utf-8")
            json.loads(manifest_content)
            latest_manifest.write_text(manifest_content, encoding="utf-8")
        except Exception as exc:
            print(f"[WARNING] Failed to update latest manifest: {exc}")

        # CRITICAL IMPROVEMENT: 배치 학습 수행
        try:
            from batch_trainer import train_from_manifest
            
            print(f"[EPOCH {epoch}/{epochs}] Starting batch training from manifest...")
            training_stats = train_from_manifest(
                manifest_path=latest_manifest,
                model_path=str(output_dir / "zerg_net_model.pt"),
                epochs=10
            )
            
            if training_stats.get("error"):
                print(f"[WARNING] Batch training had issues: {training_stats.get('error')}")
            else:
                print(f"[EPOCH {epoch}/{epochs}] Batch training completed - Loss: {training_stats.get('loss', 0):.4f}, Accuracy: {training_stats.get('accuracy', 0):.2%}")
        
        except ImportError:
            print("[WARNING] batch_trainer module not available, skipping batch training")
        except Exception as e:
            print(f"[WARNING] Batch training failed: {e}")
            import traceback
            traceback.print_exc()
        print(f"[EPOCH {epoch}/{epochs}] Selected {count} replays -> {epoch_manifest}")
        print(f"[EPOCH {epoch}/{epochs}] Latest manifest -> {latest_manifest}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run hybrid supervised selection for epochs"
    )
    parser.add_argument("--epochs", type=int, default=1, help="Number of epochs")
    parser.add_argument(
        "--max-files", type=int, default=0, help="Limit number of replays"
    )
    parser.add_argument(
        "--pro-only", action="store_true", help="Filter to known pro-player replays"
    )
    parser.add_argument(
        "--zvp-priority", action="store_true", help="Prefer ZvP replays"
    )
    parser.add_argument("--replay-dir", default=None, help="Replay directory")
    parser.add_argument(
        "--output-dir", default="data", help="Output directory for manifests"
    )
    args = parser.parse_args()

    max_files = args.max_files if args.max_files > 0 else None
    run_epochs(
        epochs=max(1, args.epochs),
        max_files=max_files,
        pro_only=args.pro_only,
        zvp_priority=args.zvp_priority,
        replay_dir=args.replay_dir,
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
