#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid trainer helpers for supervised replay manifests.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from .replay_quality_filter import ReplayQualityFilter
except ImportError:  # Fallback for script execution
    from replay_quality_filter import ReplayQualityFilter  # type: ignore[no-redef]


class HybridTrainer:
    def __init__(self, replay_dir: Optional[str] = None):
        self.replay_dir = Path(replay_dir) if replay_dir else Path("D:/replays/replays")

    def train_supervised(
        self,
        max_files: Optional[int],
        pro_only: bool,
        zvp_priority: bool,
        output_path: Path,
    ) -> int:
        filterer = ReplayQualityFilter()
        valid_replays = filterer.filter_directory(self.replay_dir)

        # Placeholder for pro_only/zvp_priority (requires metadata)
        if pro_only:
            valid_replays = valid_replays[: max_files or len(valid_replays)]
        if zvp_priority:
            valid_replays = valid_replays[: max_files or len(valid_replays)]

        if max_files:
            valid_replays = valid_replays[:max_files]

        manifest = {
            "generated_at": datetime.now().isoformat(),
            "replay_dir": str(self.replay_dir),
            "count": len(valid_replays),
            "replays": [str(path) for path in valid_replays],
            "filter_stats": filterer.stats.as_dict(),
        }

        output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return len(valid_replays)
