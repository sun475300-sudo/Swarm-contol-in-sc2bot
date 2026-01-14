#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated replay downloader and trainer.

Downloads pro Zerg replays from Sc2ReplayStats API, validates each file,
and runs supervised learning training on the collected replays.

Features:
- Fetches replays from online Sc2ReplayStats API (Zerg-focused)
- Validates downloadable files via HEAD request
- Skips already-downloaded files
- Updates manifest with new replays
- Runs training after download completion

Usage:
    python download_and_train.py --max-download 50 --epochs 2
    python download_and_train.py --local-only --epochs 1  # Skip online, train local only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import shutil
from typing import Dict, Any, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import zipfile

try:
    import requests
except ImportError:
    requests = None

import sc2reader

# Import quality filter and strategy database
try:
    from local_training.scripts.replay_quality_filter import ReplayQualityFilter
    from local_training.scripts.strategy_database import StrategyDatabase, StrategyType, MatchupType
    QUALITY_FILTER_AVAILABLE = True
except ImportError:
    QUALITY_FILTER_AVAILABLE = False
    print("[WARNING] Quality filter modules not available")

BASE_DIR = Path(__file__).resolve().parent.parent

# IMPROVED: Use flexible venv path detection
def get_venv_dir() -> Path:
    """Get virtual environment directory from environment variable or use project default"""
    venv_dir = os.environ.get("VENV_DIR")
    if venv_dir and Path(venv_dir).exists():
        return Path(venv_dir)
    # Try common locations
    possible_paths = [
        BASE_DIR / ".venv",
        Path.home() / ".venv",
        Path(".venv"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    # Default fallback
    return BASE_DIR / ".venv"

VENV_DIR = get_venv_dir()
VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe" if sys.platform == "win32" else VENV_DIR / "bin" / "python3"
PYTHON_EXECUTABLE = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

# IMPROVED: Default to D:\replays as specified in requirements
def get_replay_dir() -> Path:
    """Get replay directory - default to D:\replays"""
    # Priority 1: Environment variable
    replay_dir_env = os.environ.get("REPLAY_DIR")
    if replay_dir_env and Path(replay_dir_env).exists():
        return Path(replay_dir_env)

    # Priority 2: D:\replays (Windows default)
    default_path = Path("D:/replays")
    if default_path.exists() or sys.platform == "win32":
        return default_path

    # Priority 3: Environment variable REPLAY_ARCHIVE_DIR (backward compatibility)
    replay_archive_dir = os.environ.get("REPLAY_ARCHIVE_DIR")
    if replay_archive_dir and Path(replay_archive_dir).exists():
        return Path(replay_archive_dir)

    # Priority 4: Common locations
    possible_paths = [
        BASE_DIR / "replays",
        BASE_DIR / "replays_archive",
        Path.home() / "replays",
        Path("replays"),
    ]
    for path in possible_paths:
        if path.exists():
            return path

    # Default: D:\replays (create if doesn't exist)
    return default_path

DEFAULT_REPLAY_DIR = get_replay_dir()
# IMPROVED: Major tournaments and pro leagues (priority order)
MAJOR_TOURNAMENTS = [
    "GSL", "IEM", "ESL", "WTL", "ASUS ROG", "DreamHack", "WCS", "BlizzCon",
    "StarLeague", "HomeStory Cup", "HSC", "AfreecaTV", "Code S", "Code A",
    "Super Tournament", "Global Finals", "World Championship"
]

DEFAULT_SOURCE_PAGES = [
    "https://liquipedia.net/starcraft2/ESL_Open_Cup_EU",
    "https://liquipedia.net/starcraft2/ESL_Open_Cup_NA",
    "https://liquipedia.net/starcraft2/HomeStory_Cup",
    "https://liquipedia.net/starcraft2/GSL",
    "https://liquipedia.net/starcraft2/IEM",
]
LIQUIPEDIA_API = "https://liquipedia.net/starcraft2/api.php"
LIQUIPEDIA_BASE = "https://liquipedia.net/starcraft2/"
LIQUIPEDIA_SEARCH_TERMS = [
    "GSL", "IEM", "ESL Open Cup", "WTL", "HomeStory Cup", "HSC",
    "SC2 pro replay pack", "Spawning Tool replays",  # Google search fallback terms
]

# LotV (Legacy of the Void) release date: November 10, 2015
LOTV_RELEASE_DATE = datetime(2015, 11, 10)

# Minimum game time in seconds (5 minutes)
MIN_GAME_TIME_SECONDS = 300
DOWNLOAD_EXTENSIONS = (".sc2replay", ".zip", ".rar", ".7z")
# IMPROVED: User-Agent rotation for bypassing access blocks
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]
USER_AGENT = random.choice(USER_AGENTS) if USER_AGENTS else "WickedZergReplayDownloader/1.0"
ZERG_PRO_NAMES = {
    "serral",
    "reynor",
    "dark",
    "solar",
    "rogue",
    "soo",
    "shin",
    "drg",
    "dongraegu",
    "scarlett",
    "lambo",
    "elazer",
    "bly",
    "ragnarok",
    "armani",
    "soO".lower(),
    "jaedong",
    "snoot",
    "snute",
    "xigua",
    "losira",
    "soulkey",
    "byul",
}


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        for key, value in attrs:
            if key == "href" and value:
                self.links.append(value)


class ReplayDownloader:
    """Download and validate pro Zerg replays from online sources"""

    STATS_API = "https://sc2replaystats.com/api/v1/replays"
    TIMEOUT = 10
    RETRY_DELAY = 1.0

    def __init__(
        self,
        replay_dir: Path,
        dry_run: bool = False,
        pro_names: Optional[List[str]] = None,
        source_pages: Optional[List[str]] = None,
        liquipedia_terms: Optional[List[str]] = None,
        pro_only_download: bool = True,
    ):
        self.replay_dir = replay_dir
        self.dry_run = dry_run
        self.pro_names = {n.lower() for n in (pro_names or ZERG_PRO_NAMES)}
        self.source_pages = list(source_pages or DEFAULT_SOURCE_PAGES)
        self.liquipedia_terms = list(liquipedia_terms or LIQUIPEDIA_SEARCH_TERMS)
        self.pro_only_download = pro_only_download
        self.replay_dir.mkdir(parents=True, exist_ok=True)
        self.completed_dir = self.replay_dir / "completed"
        self.completed_dir.mkdir(parents=True, exist_ok=True)

        # IMPROVED: Incompatible replays folder for version mismatches
        self.incompatible_dir = self.replay_dir / "incompatible"
        self.incompatible_dir.mkdir(parents=True, exist_ok=True)

        # IMPROVED: Organized folder structure (by race, map, player)
        self.organized_dirs = {
            "by_race": self.replay_dir / "by_race",
            "by_map": self.replay_dir / "by_map",
            "by_player": self.replay_dir / "by_player"
        }
        for dir_path in self.organized_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

        # IMPROVED: Quality filter for advanced filtering
        if QUALITY_FILTER_AVAILABLE:
            self.quality_filter = ReplayQualityFilter(min_apm=250)
        else:
            self.quality_filter = None

        # IMPROVED: Strategy database
        if QUALITY_FILTER_AVAILABLE:
            strategy_db_path = self.replay_dir / "strategy_db.json"
            self.strategy_db = StrategyDatabase(strategy_db_path)
        else:
            self.strategy_db = None

        # IMPROVED: Track files by hash to detect duplicates
        self.existing_files = {f.name for f in self.replay_dir.glob("*.SC2Replay")}
        self.existing_hashes: Set[str] = self._scan_existing_hashes()

        self.downloaded_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.duplicate_count = 0
        self.incompatible_count = 0
        self.quality_filtered_count = 0

        # IMPROVED: Setup session with User-Agent rotation
        self.session = requests.Session() if requests else None
        if self.session:
            # Rotate User-Agent for bypassing access blocks
            self.session.headers.update({"User-Agent": random.choice(USER_AGENTS) if USER_AGENTS else USER_AGENT})

    def _scan_existing_hashes(self) -> Set[str]:
        """Scan existing replay files and return set of hashes for duplicate detection"""
        hashes = set()
        for replay_file in self.replay_dir.glob("*.SC2Replay"):
            try:
                file_hash = self._get_file_hash(replay_file)
                hashes.add(file_hash)
            except Exception:
                pass
        return hashes

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file for duplicate detection"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            # Fallback: use filename + size
            try:
                stat = file_path.stat()
                return hashlib.md5(f"{file_path.name}_{stat.st_size}".encode()).hexdigest()
            except Exception:
                return hashlib.md5(file_path.name.encode()).hexdigest()

    def _is_duplicate(self, file_path: Path) -> bool:
        """Check if file is duplicate by hash"""
        file_hash = self._get_file_hash(file_path)
        return file_hash in self.existing_hashes

    def _organize_replay_file(self, source_path: Path, filename: str) -> Path:
        """
        Organize replay file into structured folders (by race, map, player)

        Returns:
            Final path where file was moved
        """
        try:
            # Try to extract metadata for organization
            if SC2READER_AVAILABLE:
                try:
                    replay = sc2reader.load_replay(str(source_path), load_map=True)

                    # Determine matchup
                    zerg_player = None
                    opponent_race = None
                    for player in replay.players:
                        if hasattr(player, 'play_race'):
                            race = str(player.play_race).lower()
                            if race == "zerg":
                                zerg_player = player
                            else:
                                opponent_race = race

                    # Organize by matchup
                    if opponent_race:
                        matchup_dir = self.organized_dirs["by_race"] / f"Zv{opponent_race[0].upper()}"
                        matchup_dir.mkdir(parents=True, exist_ok=True)
                        target = matchup_dir / filename
                        shutil.move(str(source_path), str(target))
                        return target

                    # Organize by map
                    if hasattr(replay, 'map_name') and replay.map_name:
                        map_name = str(replay.map_name).replace(" ", "_").replace("/", "_")
                        map_dir = self.organized_dirs["by_map"] / map_name[:50]  # Limit length
                        map_dir.mkdir(parents=True, exist_ok=True)
                        target = map_dir / filename
                        shutil.move(str(source_path), str(target))
                        return target

                    # Organize by player
                    if zerg_player and hasattr(zerg_player, 'name') and zerg_player.name:
                        player_name = str(zerg_player.name).replace(" ", "_").replace("/", "_")
                        player_dir = self.organized_dirs["by_player"] / player_name[:50]
                        player_dir.mkdir(parents=True, exist_ok=True)
                        target = player_dir / filename
                        shutil.move(str(source_path), str(target))
                        return target
                except Exception:
                    pass  # Fallback to main directory

            # Fallback: Move to main directory
            target = self.replay_dir / filename
            shutil.move(str(source_path), str(target))
            return target

        except Exception as e:
            # Fallback: Move to main directory
            target = self.replay_dir / filename
            try:
                shutil.move(str(source_path), str(target))
            except Exception:
                pass
            return target

    def _match_pro_name(self, text: str) -> bool:
        lower = text.lower()
        return any(name in lower for name in self.pro_names)

    def _is_pro_tournament(self, replay_meta: Dict[str, Any]) -> bool:
        """Check if replay is from major tournament or pro player"""
        # Check tournament name
        tournament = str(replay_meta.get("tournament", "")).upper()
        for major in MAJOR_TOURNAMENTS:
            if major.upper() in tournament:
                return True

        # Check player names
        player1_name = str(replay_meta.get("player1_name", "")).lower()
        player2_name = str(replay_meta.get("player2_name", "")).lower()

        for pro_name in self.pro_names:
            if pro_name.lower() in player1_name or pro_name.lower() in player2_name:
                return True

        return False

    def _google_search_fallback(self, search_terms: List[str]) -> List[str]:
        """
        Fallback: Search Google for replay pack links when site is blocked

        Args:
            search_terms: List of search terms (e.g., ['SC2 pro replay pack', 'Spawning Tool replays'])

        Returns:
            List of potential replay download URLs
        """
        if not self.session:
            return []

        found_urls = []
        for term in search_terms:
            try:
                # Use Google Custom Search API or scrape Google search results
                # For now, log the search term (requires API key or scraping setup)
                print(f"[FALLBACK] Google search for: {term}")
                # TODO: Implement Google search API integration or web scraping
                time.sleep(self.RETRY_DELAY)
            except Exception as e:
                print(f"[FALLBACK ERROR] {e}")

        return found_urls

    def _http_head(self, url: str):
        if not self.session:
            return None
        try:
            return self.session.head(url, timeout=self.TIMEOUT, allow_redirects=True)
        except Exception:
            return None

    def _http_get(self, url: str):
        if not self.session:
            return None
        try:
            return self.session.get(url, timeout=self.TIMEOUT, allow_redirects=True)
        except Exception:
            return None

    def _extract_archive(self, archive_path: Path) -> int:
        """
        Extract archive file (ZIP, RAR, 7Z) and return count of extracted replays

        IMPROVED: Validates each extracted replay and removes duplicates
        """
        if not archive_path.exists():
            return 0
        extracted = 0
        archive_dir = self.replay_dir / "_archives"
        archive_dir.mkdir(parents=True, exist_ok=True)

        if archive_path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(archive_path, "r") as zf:
                    for member in zf.infolist():
                        if not member.filename.lower().endswith(".sc2replay"):
                            continue
                        filename = Path(member.filename).name

                        # Check if already exists by name
                        if filename in self.existing_files:
                            self.skipped_count += 1
                            continue

                        # Extract to temp location first
                        temp_target = self.replay_dir / "_temp" / filename
                        temp_target.parent.mkdir(parents=True, exist_ok=True)

                        with zf.open(member, "r") as src, temp_target.open("wb") as dst:
                            shutil.copyfileobj(src, dst)

                        # Check for duplicates by hash
                        if self._is_duplicate(temp_target):
                            print(f"  [DUPLICATE] {filename}")
                            temp_target.unlink()
                            self.duplicate_count += 1
                            continue

                        # Validate replay metadata with quality filtering
                        is_valid, error_msg, is_incompatible = self._validate_replay_metadata(temp_target)
                        if not is_valid:
                            if is_incompatible:
                                # Move to incompatible folder
                                incompatible_target = self.incompatible_dir / filename
                                try:
                                    shutil.move(str(temp_target), str(incompatible_target))
                                    print(f"  [INCOMPATIBLE] {filename}: Moved to incompatible folder")
                                    self.incompatible_count += 1
                                except Exception as e:
                                    print(f"  [ERROR] Failed to move incompatible file: {e}")
                                    temp_target.unlink()
                            else:
                                print(f"  [INVALID] {filename}: {error_msg}")
                                temp_target.unlink()
                                if self.quality_filter:
                                    self.quality_filtered_count += 1
                            self.failed_count += 1
                            continue

                        # Move to final location (with optional organization)
                        target = self._organize_replay_file(temp_target, filename)
                        self.existing_files.add(filename)
                        self.existing_hashes.add(self._get_file_hash(target))
                        extracted += 1
                        print(f"  [EXTRACTED] {filename}")
            except Exception as exc:
                print(f"  [ARCHIVE ERROR] {archive_path.name}: {exc}")
        else:
            print(f"  [ARCHIVE SKIP] Unsupported archive format: {archive_path.name}")
            return 0
        return extracted

    def download_and_extract_from_url(self, url: str) -> int:
        """
        IMPROVED: Download from URL with enhanced validation and duplicate detection
        """
        """
        IMPROVED: Unified download method - download from URL and extract if archive
        This replaces the functionality from replay_downloader.py
        """
        import urllib.request
        import urllib.parse
        import urllib.error

        # Parse URL to determine file type
        parsed_url = urllib.parse.urlparse(url)
        file_name = os.path.basename(parsed_url.path) or "downloaded_file"
        temp_file = self.replay_dir / "_temp" / file_name
        temp_file.parent.mkdir(parents=True, exist_ok=True)

        # Download file
        try:
            print(f"  [DOWNLOADING] {file_name} from {url}...")
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'WickedZergReplayDownloader/1.0')

            with urllib.request.urlopen(req, timeout=30) as response:
                with open(temp_file, 'wb') as f:
                    shutil.copyfileobj(response, f)
            print(f"    [OK] Downloaded {file_name}")
        except Exception as e:
            print(f"    [FAILED] Download error: {e}")
            return 0

        # Extract if archive, otherwise move single file
        new_count = 0
        if file_name.lower().endswith(('.zip', '.rar', '.7z')):
            new_count = self._extract_archive(temp_file)
            # Clean up temp file
            try:
                temp_file.unlink()
            except Exception:
                pass
        elif file_name.lower().endswith('.sc2replay'):
            # Single replay file - validate and move to replay directory
            # Check for duplicates by hash
            if self._is_duplicate(temp_file):
                print(f"    [DUPLICATE] Removing duplicate file")
                temp_file.unlink()
                self.duplicate_count += 1
                return 0

            # Validate replay metadata with quality filtering
            is_valid, error_msg, is_incompatible = self._validate_replay_metadata(temp_file)
            if not is_valid:
                if is_incompatible:
                    # Move to incompatible folder
                    incompatible_target = self.incompatible_dir / file_name
                    try:
                        shutil.move(str(temp_file), str(incompatible_target))
                        print(f"    [INCOMPATIBLE] Moved to incompatible folder: {error_msg}")
                        self.incompatible_count += 1
                    except Exception as e:
                        print(f"    [ERROR] Failed to move incompatible file: {e}")
                        temp_file.unlink()
                    self.failed_count += 1
                else:
                    print(f"    [INVALID] {error_msg}")
                    temp_file.unlink()
                    self.failed_count += 1
                    if self.quality_filter:
                        self.quality_filtered_count += 1
                return 0

            target = self.replay_dir / file_name
            if file_name not in self.existing_files:
                try:
                    shutil.move(str(temp_file), str(target))
                    self.existing_files.add(file_name)
                    self.existing_hashes.add(self._get_file_hash(target))
                    new_count = 1
                    print(f"    [VALIDATED] {file_name}")
                except Exception as e:
                    print(f"    [ERROR] Failed to move file: {e}")
            else:
                self.skipped_count += 1
                try:
                    temp_file.unlink()
                except Exception:
                    pass

        return new_count

    def _is_downloadable(self, download_url: Optional[str]) -> bool:
        if not download_url or not self.session:
            return False
        resp = self._http_head(download_url)
        if not resp:
            return False
        if resp.status_code != 200:
            return False
        content_type = resp.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            return False
        length = resp.headers.get("Content-Length")
        if length:
            try:
                if int(length) < 10240:
                    return False
            except ValueError:
                pass
        return True

    def _normalize_filename(self, url: str) -> str:
        path = urlparse(url).path
        name = Path(path).name
        if name:
            return name
        return f"download_{int(time.time())}.SC2Replay"

    def _fetch_page_links(self, url: str) -> List[str]:
        resp = self._http_get(url)
        if not resp or resp.status_code != 200:
            return []
        parser = LinkExtractor()
        parser.feed(resp.text)
        return parser.links

    def _liquipedia_search_pages(self) -> List[str]:
        if not self.session:
            return []
        pages: List[str] = []
        for term in self.liquipedia_terms:
            try:
                resp = self.session.get(
                    LIQUIPEDIA_API,
                    params={
                        "action": "opensearch",
                        "search": term,
                        "limit": "6",
                        "format": "json",
                    },
                    timeout=self.TIMEOUT,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                if isinstance(data, list) and len(data) >= 2:
                    pages.extend(data[1])
                time.sleep(self.RETRY_DELAY)
            except Exception:
                continue
        return list(dict.fromkeys(pages))

    def _liquipedia_page_links(self, page_title: str) -> List[str]:
        if not self.session:
            return []
        try:
            resp = self.session.get(
                LIQUIPEDIA_API,
                params={
                    "action": "parse",
                    "page": page_title,
                    "prop": "text",
                    "format": "json",
                },
                timeout=self.TIMEOUT,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            html = data.get("parse", {}).get("text", {}).get("*", "")
            parser = LinkExtractor()
            parser.feed(html)
            return parser.links
        except Exception:
            return []

    def fetch_replay_pack_links(self, max_links: int = 50) -> List[str]:
        if not self.session:
            print("[DOWNLOAD] requests library not available; skipping web scraping")
            return []

        links: List[str] = []
        for url in self.source_pages:
            links.extend(self._fetch_page_links(url))
            time.sleep(self.RETRY_DELAY)

        for page in self._liquipedia_search_pages():
            links.extend(self._liquipedia_page_links(page))
            time.sleep(self.RETRY_DELAY)

        filtered: List[str] = []
        seen = set()
        for link in links:
            if not link:
                continue
            absolute = urljoin(LIQUIPEDIA_BASE, link)
            path = urlparse(absolute).path
            ext = Path(path).suffix.lower()
            if ext not in DOWNLOAD_EXTENSIONS:
                if "replay" not in absolute.lower():
                    continue
            name = Path(path).name or absolute
            if ext == ".sc2replay" and self.pro_only_download and not self._match_pro_name(name):
                continue
            if absolute in seen:
                continue
            seen.add(absolute)
            filtered.append(absolute)
            if len(filtered) >= max_links:
                break

        if filtered:
            print(f"[WEB] Found {len(filtered)} replay pack links")
        else:
            print("[WEB] No replay pack links found")
        return filtered

    def _is_zerg_involved(self, replay_meta: Dict[str, Any]) -> bool:
        """
        Check if replay involves Zerg player (ZvT, ZvP, ZvZ)
        IMPROVED: Strict Zerg matchup filtering
        """
        player1_race = str(replay_meta.get("player1_play_race", "")).lower()
        player2_race = str(replay_meta.get("player2_play_race", "")).lower()
        return "zerg" in player1_race or "zerg" in player2_race

    def _validate_replay_metadata(self, replay_path: Path) -> Tuple[bool, Optional[str], bool]:
        """
        Validate replay using sc2reader metadata with advanced quality filtering

        Requirements:
        - sc2reader compatibility
        - Game time >= 5 minutes and <= 30 minutes
        - LotV patch (after Nov 10, 2015)
        - Zerg player present
        - APM >= 250 (if quality filter available)
        - Official ladder map (preferred)

        Returns:
            (is_valid, error_message, is_incompatible)
        """
        if not SC2READER_AVAILABLE:
            return True, None, False  # Skip validation if sc2reader not available

        try:
            replay = sc2reader.load_replay(str(replay_path), load_map=True)

            # 1. Check if replay has players
            if not hasattr(replay, 'players') or len(replay.players) < 2:
                return False, "Invalid replay structure: insufficient players", False

            # 2. Check if at least one player is Zerg
            has_zerg = False
            zerg_player = None
            for player in replay.players:
                if hasattr(player, 'play_race'):
                    race = str(player.play_race).lower()
                    if race == "zerg":
                        has_zerg = True
                        zerg_player = player
                        break

            if not has_zerg:
                return False, "No Zerg player found", False

            # 3. Check game time (minimum 5 minutes, maximum 30 minutes)
            if hasattr(replay, 'length'):
                game_seconds = replay.length.seconds
                if game_seconds < MIN_GAME_TIME_SECONDS:
                    return False, f"Game too short: {game_seconds}s < {MIN_GAME_TIME_SECONDS}s", False
                if game_seconds > 1800:  # 30 minutes
                    return False, f"Game too long: {game_seconds}s > 1800s", False

            # 4. Check LotV patch (replay date should be after LotV release)
            if hasattr(replay, 'date'):
                replay_date = replay.date
                if replay_date < LOTV_RELEASE_DATE:
                    return False, f"Pre-LotV replay: {replay_date.date()} < {LOTV_RELEASE_DATE.date()}", False

            # 5. Advanced quality filtering (if available)
            if self.quality_filter:
                is_valid, validation_details = self.quality_filter.validate_replay_quality(replay_path)
                if not is_valid:
                    # Check if incompatible (version mismatch)
                    if validation_details.get("incompatible", False):
                        return False, validation_details.get("errors", ["Version incompatible"])[0], True
                    # Quality filter failed
                    error_msg = "; ".join(validation_details.get("errors", []))
                    return False, f"Quality filter failed: {error_msg}", False

            return True, None, False

        except Exception as e:
            error_msg = str(e)
            # Check if it's a version incompatibility error
            if "version" in error_msg.lower() or "incompatible" in error_msg.lower():
                return False, f"Version incompatible: {error_msg}", True
            return False, f"Validation error: {str(e)}", False

    def _is_downloadable(self, download_url: Optional[str]) -> bool:
        """Validate if URL is downloadable via HEAD request"""
        if not download_url or not requests:
            return False
        try:
            resp = requests.head(download_url, timeout=self.TIMEOUT, allow_redirects=True)
            return resp.status_code == 200
        except Exception:
            return False

    def fetch_replays_from_api(self, max_replays: int = 50, page_size: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch pro Zerg replays from Sc2ReplayStats API

        IMPROVED: Filters for Zerg matchups only, prioritizes pro tournaments
        """
        if not requests and not self.session:
            print("[DOWNLOAD] requests library not available; skipping API fetch")
            # Try Google search fallback
            return self._google_search_fallback(LIQUIPEDIA_SEARCH_TERMS)

        print(f"[DOWNLOAD] Fetching replays from {self.STATS_API}")
        all_replays = []
        page = 1
        max_pages = (max_replays // page_size) + 1

        try:
            while len(all_replays) < max_replays and page <= max_pages:
                url = f"{self.STATS_API}?pageSize={page_size}&page={page}"
                print(f"  [PAGE {page}] Fetching {page_size} replays...")

                # Try with session first, fallback to requests
                if self.session:
                    resp = self.session.get(url, timeout=self.TIMEOUT)
                else:
                    resp = requests.get(url, timeout=self.TIMEOUT)

                if resp.status_code == 403 or resp.status_code == 429:
                    # Access blocked - try Google search fallback
                    print(f"  [BLOCKED] Access blocked (HTTP {resp.status_code}), trying Google search fallback...")
                    fallback_urls = self._google_search_fallback(LIQUIPEDIA_SEARCH_TERMS)
                    if fallback_urls:
                        print(f"  [FALLBACK] Found {len(fallback_urls)} alternative URLs")
                    break

                resp.raise_for_status()
                data = resp.json()

                replays = data.get("results", [])
                if not replays:
                    print("  [API] No more replays available")
                    break

                # Filter: Zerg matchups only
                zerg_replays = [r for r in replays if self._is_zerg_involved(r)]

                # Prioritize pro tournaments (sort by tournament priority)
                prioritized = []
                for r in zerg_replays:
                    if self._is_pro_tournament(r):
                        prioritized.insert(0, r)  # Add to front
                    else:
                        prioritized.append(r)

                print(f"    - Got {len(zerg_replays)} Zerg matchups from {len(replays)} total")
                print(f"    - Pro tournaments: {len([r for r in zerg_replays if self._is_pro_tournament(r)])}")
                all_replays.extend(prioritized)
                page += 1
                time.sleep(self.RETRY_DELAY)  # Rate limiting
        except Exception as e:
            print(f"[API ERROR] {e}")
            # Try Google search fallback on error
            print(f"[FALLBACK] Trying Google search fallback...")
            fallback_urls = self._google_search_fallback(LIQUIPEDIA_SEARCH_TERMS)
            if fallback_urls:
                print(f"[FALLBACK] Found {len(fallback_urls)} alternative URLs")

        print(f"[DOWNLOAD] Total Zerg replays from API: {len(all_replays)}")
        return all_replays[:max_replays]

    def download_replay(self, replay_meta: Dict[str, Any]) -> Optional[Path]:
        """
        Download and validate a single replay

        IMPROVED: Enhanced validation and duplicate detection
        """
        # 1. Filter: Zerg matchup only (ZvT, ZvP, ZvZ)
        if not self._is_zerg_involved(replay_meta):
            return None

        # 2. Priority: Pro tournament/player (optional - can be enabled)
        # Uncomment to enable strict pro-only filtering:
        # if not self._is_pro_tournament(replay_meta):
        #     return None

        filename = replay_meta.get("filename") or f"replay_{replay_meta.get('id', 'unknown')}.SC2Replay"

        # Check if already exists by name
        if filename in self.existing_files:
            self.skipped_count += 1
            return None

        download_url = replay_meta.get("url") or replay_meta.get("download_url")
        if not download_url:
            print(f"  [SKIP] {filename} - no download URL")
            self.skipped_count += 1
            return None

        # Validate URL before downloading
        if not self._is_downloadable(download_url):
            print(f"  [INVALID] {filename} - URL not accessible")
            self.failed_count += 1
            return None

        if self.dry_run:
            print(f"  [DRY-RUN] Would download: {filename} from {download_url}")
            self.downloaded_count += 1
            return None

        try:
            print(f"  [DOWNLOADING] {filename}...")
            resp = self.session.get(download_url, timeout=self.TIMEOUT) if self.session else None
            if not resp:
                resp = requests.get(download_url, timeout=self.TIMEOUT)
            resp.raise_for_status()

            # Write to temp file first for validation
            temp_path = self.replay_dir / "_temp" / filename
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_bytes(resp.content)

            # Check for duplicates by hash
            if self._is_duplicate(temp_path):
                print(f"    [DUPLICATE] Removing duplicate file")
                temp_path.unlink()
                self.duplicate_count += 1
                return None

            # Validate replay metadata with quality filtering
            is_valid, error_msg, is_incompatible = self._validate_replay_metadata(temp_path)
            if not is_valid:
                if is_incompatible:
                    # Move to incompatible folder
                    incompatible_target = self.incompatible_dir / filename
                    try:
                        shutil.move(str(temp_path), str(incompatible_target))
                        print(f"    [INCOMPATIBLE] Moved to incompatible folder: {error_msg}")
                        self.incompatible_count += 1
                    except Exception as e:
                        print(f"    [ERROR] Failed to move incompatible file: {e}")
                        temp_path.unlink()
                else:
                    print(f"    [INVALID] {error_msg}")
                    temp_path.unlink()
                    if self.quality_filter:
                        self.quality_filtered_count += 1
                self.failed_count += 1
                return None

            # Move to final location (with optional organization)
            output_path = self._organize_replay_file(temp_path, filename)
            self.existing_files.add(filename)
            self.existing_hashes.add(self._get_file_hash(output_path))
            print(f"    [OK] Downloaded and validated ({len(resp.content) / (1024 * 1024):.1f} MB)")
            self.downloaded_count += 1
            return output_path
        except Exception as e:
            print(f"    [FAILED] Failed: {e}")
            self.failed_count += 1
            return None

    def scan_local_replays(self) -> List[Path]:
        """
        Scan local replay directory for new files with enhanced validation

        IMPROVED: Validates game time (5+ minutes), LotV patch, Zerg presence
        """
        print(f"[LOCAL] Scanning {self.replay_dir}")
        local_replays = list(self.replay_dir.glob("*.SC2Replay"))
        valid_replays = []
        invalid_count = 0

        for rp in local_replays:
            # Skip completed folder
            if self.completed_dir in rp.parents:
                continue

            # Validate replay with quality filtering
            is_valid, error_msg, is_incompatible = self._validate_replay_metadata(rp)
            if is_valid:
                valid_replays.append(rp)
                print(f"  [OK] {rp.name}")
            else:
                invalid_count += 1
                if is_incompatible:
                    # Move to incompatible folder
                    incompatible_target = self.incompatible_dir / rp.name
                    try:
                        shutil.move(str(rp), str(incompatible_target))
                        print(f"  [INCOMPATIBLE] {rp.name} - Moved to incompatible folder")
                        self.incompatible_count += 1
                    except Exception as e:
                        print(f"  [ERROR] Failed to move incompatible file: {e}")
                else:
                    print(f"  [INVALID] {rp.name} - {error_msg}")
                    if self.quality_filter:
                        self.quality_filtered_count += 1

        print(f"[LOCAL] Found {len(valid_replays)} valid replays, {invalid_count} invalid")
        return valid_replays

    def run_download(self, max_replays: int = 50) -> List[Path]:
        """Execute full download + local scan workflow"""
        print("\n" + "=" * 80)
        print("REPLAY DOWNLOADER")
        print("=" * 80 + "\n")

        downloaded = []

        # Fetch from API
        api_replays = self.fetch_replays_from_api(max_replays=max_replays)
        for meta in api_replays:
            path = self.download_replay(meta)
            if path:
                downloaded.append(path)
            time.sleep(self.RETRY_DELAY)

        # Scan local
        print()
        local_replays = self.scan_local_replays()

        print(f"\n[SUMMARY]")
        print(f"  Downloaded: {self.downloaded_count}")
        print(f"  Skipped (already present): {self.skipped_count}")
        print(f"  Duplicates removed: {self.duplicate_count}")
        print(f"  Failed: {self.failed_count}")
        if self.incompatible_count > 0:
            print(f"  Incompatible (moved to incompatible/): {self.incompatible_count}")
        if self.quality_filtered_count > 0:
            print(f"  Quality filtered: {self.quality_filtered_count}")
        print(f"  Total valid local replays: {len(local_replays)}")
        if self.quality_filter:
            stats = self.quality_filter.get_stats()
            print(f"\n[QUALITY FILTER STATS]")
            print(f"  Total checked: {stats.get('total_checked', 0)}")
            print(f"  Passed APM check: {stats.get('passed_apm', 0)}")
            print(f"  Passed opponent check: {stats.get('passed_opponent', 0)}")
            print(f"  Passed map check: {stats.get('passed_map', 0)}")
            print(f"  Passed all checks: {stats.get('passed_all', 0)}")
        print()

        return downloaded + local_replays


class ManifestBuilder:
    """Build manifest from collected replays"""

    def __init__(self, replay_dir: Path):
        self.replay_dir = replay_dir

    def build_manifest(self, replays: List[Path], output_path: Path) -> Dict[str, Any]:
        """Build manifest JSON from replay list"""
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "replay_dir": str(self.replay_dir),
            "count": len(replays),
            "replays": [{"path": str(rp), "filename": rp.name} for rp in replays],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"[MANIFEST] Saved to {output_path} ({len(replays)} replays)")
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Download pro Zerg replays and run training")
    parser.add_argument("--max-download", type=int, default=20, help="Max replays to download from API (default: 20)")
    parser.add_argument("--local-only", action="store_true", help="Use existing manifest + skip online download")
    parser.add_argument("--skip-download", action="store_true", help="Skip all downloads, run training on existing manifest")
    parser.add_argument("--dry-run", action="store_true", help="Validate URLs without downloading")
    parser.add_argument("--replay-dir", default=str(DEFAULT_REPLAY_DIR), help="Replay directory (default: auto-detect)")
    parser.add_argument("--manifest-input", default=str(BASE_DIR / "data" / "hybrid_learning_manifest.json"), help="Existing manifest path (for resume)")
    parser.add_argument("--manifest-output", default=str(BASE_DIR / "data" / "hybrid_learning_manifest.json"), help="Manifest output path")
    parser.add_argument("--epochs", type=int, default=2, help="Training epochs (default: 2)")
    parser.add_argument("--zerg-only", action="store_true", default=True, help="Train only on Zerg replays (default: True)")
    parser.add_argument("--no-zerg-only", dest="zerg_only", action="store_false", help="Disable Zerg-only filtering")
    args = parser.parse_args()

    replay_dir = Path(args.replay_dir)
    if not replay_dir.is_absolute():
        replay_dir = (BASE_DIR / replay_dir).resolve()

    manifest_path = Path(args.manifest_output)
    if not manifest_path.is_absolute():
        manifest_path = (BASE_DIR / manifest_path).resolve()

    # Check if we should skip all processing and use existing manifest
    if args.skip_download and manifest_path.exists():
        print(f"[SKIP] Using existing manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        all_replays = [Path(r.get("path") or r) for r in manifest.get("replays", [])]
    else:
        # Download replays
        downloader = ReplayDownloader(replay_dir, dry_run=args.dry_run)
        if args.local_only:
            print("[INFO] Local-only mode: scanning local directory only")
            all_replays = downloader.scan_local_replays()
        else:
            all_replays = downloader.run_download(max_replays=args.max_download)

        # IMPROVED: Enhanced fallback mechanism for manifest corruption or missing files
        if not all_replays:
            manifest_valid = False
            if manifest_path.exists():
                print(f"[FALLBACK] No replays found locally; attempting to use manifest: {manifest_path}")
                try:
                    manifest_content = manifest_path.read_text(encoding="utf-8")
                    if not manifest_content.strip():
                        print(f"[WARNING] Manifest file is empty, will attempt local scan")
                    else:
                        manifest = json.loads(manifest_content)
                        all_replays = [Path(r.get("path") or r) for r in manifest.get("replays", [])]
                        # Validate that replay files actually exist
                        valid_replays = [rp for rp in all_replays if rp.exists()]
                        if valid_replays:
                            print(f"[FALLBACK] Loaded {len(valid_replays)} valid replays from manifest (out of {len(all_replays)} total)")
                            all_replays = valid_replays
                            manifest_valid = True
                        else:
                            print(f"[WARNING] Manifest contains {len(all_replays)} replays but none exist on disk")
                except json.JSONDecodeError as e:
                    print(f"[WARNING] Manifest file is corrupted (invalid JSON): {e}")
                    print(f"[FALLBACK] Attempting to scan local directory for replays...")
                except Exception as e:
                    print(f"[WARNING] Failed to load manifest: {e}")
                    print(f"[FALLBACK] Attempting to scan local directory for replays...")

            # IMPROVED: Auto-rescan local directory if manifest is invalid or missing
            if not manifest_valid and not all_replays:
                print("[FALLBACK] Manifest invalid or missing, scanning local directory...")
                try:
                    local_replays = downloader.scan_local_replays()
                    if local_replays:
                        print(f"[FALLBACK] Found {len(local_replays)} replays in local directory")
                        all_replays = local_replays
                    else:
                        print("[WARNING] No replays found in local directory either")
                except Exception as e:
                    print(f"[WARNING] Local directory scan failed: {e}")

            if not all_replays:
                print("[ERROR] No replays found and no valid manifest. Training will be skipped.")
                print("[INFO] Options:")
                print("  1. Run with --local-only to force local directory scan")
                print("  2. Download replays first using --max-download N")
                print("  3. Check replay directory path and ensure replays exist")
                return

    # Build manifest (or skip if using existing)
    builder = ManifestBuilder(replay_dir)
    manifest = builder.build_manifest(all_replays, manifest_path)

    # Run training
    print("\n" + "=" * 80)
    print("STARTING SUPERVISED TRAINING")
    print("=" * 80 + "\n")

    try:
        import subprocess
        train_script = BASE_DIR / "scripts" / "train_replay_supervised.py"
        cmd = [
            PYTHON_EXECUTABLE,
            str(train_script),
            "--manifest",
            str(manifest_path),
            "--epochs",
            str(args.epochs),
        ]
        if args.zerg_only:
            cmd.append("--zerg-only")
        else:
            cmd.append("--no-zerg-only")

        print(f"[RUN] {' '.join(cmd)}\n")
        result = subprocess.run(cmd, check=False, cwd=BASE_DIR)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"[ERROR] Failed to run training: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
