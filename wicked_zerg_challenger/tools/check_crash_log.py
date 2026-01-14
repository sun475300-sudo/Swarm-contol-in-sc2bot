#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check and clear crash_log.json in_progress entries"""

import json
from pathlib import Path

crash_log = Path("D:/replays/replays/crash_log.json")

if crash_log.exists():
    data = json.loads(crash_log.read_text(encoding='utf-8'))
    in_progress = data.get('in_progress', {})
    print(f"Current in_progress entries: {len(in_progress)}")

    if in_progress:
        print("\nFirst 5 entries:")
        for i, (key, value) in enumerate(list(in_progress.items())[:5]):
            print(f"  {i+1}. {value.get('filename', 'unknown')} - {value.get('start_time', 'no time')}")

        print("\nClearing in_progress entries...")
        data['in_progress'] = {}
        crash_log.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        print("[OK] Cleared all in_progress entries")
    else:
        print("[OK] No in_progress entries (already clear)")
else:
    print("crash_log.json does not exist (will be created on first run)")
