"""
Log Collector - Collects error logs from a given directory.
"""

from pathlib import Path
from typing import List


class LogCollector:
    """Collects error logs from a given directory."""

    def __init__(self, log_dir: str = "logs") -> None:
        """
        Initialize LogCollector.
        
        Args:
            log_dir: Directory path to collect logs from
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def collect(self) -> List[str]:
        """
        Collect all log messages from log directory.
        
        Returns:
            List of log message lines
        """
        messages: List[str] = []
        
        # Collect from .log files
        for path in self.log_dir.glob("*.log"):
            try:
                content = path.read_text(encoding="utf-8")
                messages.extend(content.splitlines())
            except (IOError, UnicodeDecodeError) as e:
                # Skip files that can't be read
                print(f"[WARNING] Failed to read log file {path}: {e}")
                continue
        
        # Collect from .txt files (backup)
        for path in self.log_dir.glob("*.txt"):
            if path.name == "training_log.txt":  # Skip training logs
                continue
            try:
                content = path.read_text(encoding="utf-8")
                messages.extend(content.splitlines())
            except (IOError, UnicodeDecodeError):
                continue
        
        return messages
