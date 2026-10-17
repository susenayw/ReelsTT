from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import sys

APP_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', APP_DIR))
def default_data_directory():
    override = os.environ.get('REELSTT_DATA_DIR')
    if override:
        return Path(override)
    # Existing portable copies retain their data. New installed builds use a
    # stable directory outside Velopack's versioned application files.
    legacy = APP_DIR / 'data'
    if not getattr(sys, 'frozen', False) or (legacy / 'config.json').is_file():
        return legacy
    local = os.environ.get('LOCALAPPDATA')
    return (Path(local) if local else Path.home() / 'AppData' / 'Local') / 'ReelsTT'


DATA_DIR = default_data_directory()
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = DATA_DIR / 'thumbnails'
CACHE_DIR.mkdir(exist_ok=True)


class Config:
    """Single-writer, atomic local preferences. Original media is never modified."""

    def __init__(self, directory: Path | None = None):
        self.path = (directory or DATA_DIR) / 'config.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = {'folders': [], 'favorites': [], 'volume': 70, 'muted': False,
                     'loop': True, 'recursive': True, 'view': 'grid',
                     'sort': 'recent', 'window': [1280, 870], 'onboarded': False}
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(raw, dict):
                    raise ValueError('Settings must be a JSON object')
                for key, value in raw.items():
                    if key in self.data and isinstance(value, type(self.data[key])):
                        self.data[key] = value
                self.data['folders'] = [p for p in self.data['folders'] if isinstance(p, str)]
                self.data['favorites'] = [p for p in self.data['favorites'] if isinstance(p, str)]
                self.data['volume'] = max(0, min(100, self.data['volume']))
                window = self.data['window']
                if len(window) != 2 or not all(isinstance(v, int) for v in window):
                    self.data['window'] = [1280, 870]
            except (ValueError, OSError):
                logging.exception('Unable to read preferences; keeping original file as config.broken.json')
                try:
                    self.path.replace(self.path.with_name('config.broken.json'))
                except OSError:
                    pass

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def save(self):
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding='utf-8')
        temporary.replace(self.path)

    def add_folder(self, path: str) -> bool:
        path = str(Path(path).resolve())
        if any(os.path.normcase(p) == os.path.normcase(path) for p in self.data['folders']):
            return False
        self.data['folders'].insert(0, path)
        self.save()
        return True

    def toggle_favorite(self, path: str) -> bool:
        paths = self.data['favorites']
        if path in paths:
            paths.remove(path)
            self.save()
            return False
        paths.append(path)
        self.save()
        return True
