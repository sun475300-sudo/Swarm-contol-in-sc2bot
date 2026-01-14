# SC2 AI Monitoring - Quick Start

This folder provides a real-time monitoring stack for your StarCraft II bot with two run modes:

- Single-port (recommended): FastAPI serves UI + API + WebSocket on one port
- Dual-port (legacy): dashboard.py (UI+WS) on 8000 and FastAPI API on 8001

## Run (Single Port)

```powershell
# Optional: set data base dir (defaults to current working directory)
$env:MONITORING_BASE_DIR="D:\wicked_zerg_challenger"
# Optional: restrict API CORS (defaults to local origins)
$env:MONITORING_ALLOWED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000"

# Start FastAPI on 8000
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000
```

- UI: http://localhost:8000/ui
- WebSocket: ws://localhost:8000/ws/game-status (alias) or /ws/game-state
- REST: http://localhost:8000/api/game-state (and others)

## Run (Legacy Dual Port)

```powershell
# Start dashboard server (serves static UI and WS on dynamic or 8000)
python dashboard.py

# Optionally start the FastAPI backend
uvicorn dashboard_api:app --host 0.0.0.0 --port 8001
```

## Data Source Resolution

The servers locate your training data as follows:

1. `MONITORING_BASE_DIR` environment variable, if set
2. Otherwise, `Path.cwd()` (the current working directory where you launch)

Expected files (either under base dir or its subfolders):
- `stats/instance_*_status.json` (latest game state)
- `data/training_stats.json` or `training_stats.json` (training progress)

## Environment Variables

- `MONITORING_BASE_DIR`: Absolute or relative path to folder containing telemetry JSON files
- `MONITORING_ALLOWED_ORIGINS`: Comma-separated list of allowed origins for CORS (FastAPI only)
- `DASHBOARD_PORT` / `PORT`: Port override for dashboard.py mode
- `START_FASTAPI=1`: Auto-start FastAPI backend from dashboard.py (port 8001)

## Frontend Notes

- `dashboard.html` now uses same-origin URLs for WebSocket and REST
- No hardcoded `localhost:8000` ? works on any host/port
- WebSocket message format is consistent across both servers:
  ```json
  {
    "type": "game_status",
    "game_state": { /* metrics */ },
    "units": { /* unit counts */ },
    "timestamp": "ISO-8601"
  }
  ```

## Troubleshooting

- No data updating?
  - Confirm JSON files exist under `MONITORING_BASE_DIR` or CWD
  - Check FastAPI logs for CORS blocks ? set `MONITORING_ALLOWED_ORIGINS`
  - Verify WebSocket path `/ws/game-status` is reachable
- Wrong folder used?
  - Print `get_base_dir()` or set `MONITORING_BASE_DIR` explicitly
