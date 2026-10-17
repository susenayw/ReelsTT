from __future__ import annotations

import hashlib
import logging
from pathlib import Path
import queue
import subprocess
import threading

from PySide6.QtCore import QThread, Signal

from core.config import CACHE_DIR


def cache_path(path: str) -> Path:
    source = Path(path)
    try:
        stamp = f'{source.stat().st_mtime_ns}-{source.stat().st_size}'
    except OSError:
        stamp = ''
    return CACHE_DIR / (hashlib.sha256((path + stamp).encode()).hexdigest() + '.jpg')


class ThumbnailWorker(QThread):
    ready = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.jobs = queue.Queue()
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._process = None
        self._lock = threading.Lock()
        self.pending = set()

    def request(self, path: str):
        target = cache_path(path)
        if target.exists():
            self.ready.emit(path, str(target))
        elif path not in self.pending:
            self.pending.add(path)
            self.jobs.put(path)

    def pause(self, paused: bool):
        if paused:
            self._paused.set()
            with self._lock:
                if self._process and self._process.poll() is None:
                    self._process.kill()
        else:
            self._paused.clear()

    def shutdown(self):
        self._stop.set()
        self.pause(True)
        self.wait(6000)

    def run(self):
        import imageio_ffmpeg
        executable = imageio_ffmpeg.get_ffmpeg_exe()
        while not self._stop.is_set():
            if self._paused.is_set():
                self._stop.wait(.15)
                continue
            try:
                path = self.jobs.get(timeout=.2)
            except queue.Empty:
                continue
            target = cache_path(path)
            temporary = target.with_suffix('.tmp.jpg')
            success = False
            try:
                args = [executable, '-hide_banner', '-loglevel', 'error', '-threads', '1',
                        '-filter_threads', '1', '-ss', '0', '-i', path, '-an', '-sn',
                        '-frames:v', '1', '-vf', 'scale=480:270:force_original_aspect_ratio=increase,crop=480:270',
                        '-threads', '1', '-q:v', '5', '-y', str(temporary)]
                with self._lock:
                    if self._paused.is_set() or self._stop.is_set():
                        self.jobs.put(path)
                        continue
                    self._process = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                try:
                    success = self._process.wait(timeout=15) == 0 and temporary.exists()
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()
                if success:
                    temporary.replace(target)
                    self.ready.emit(path, str(target))
                elif self._paused.is_set():
                    self.jobs.put(path)
                    continue
            except Exception:
                logging.exception('Thumbnail failed: %s', path)
            finally:
                with self._lock:
                    self._process = None
                temporary.unlink(missing_ok=True)
            self.pending.discard(path)
        self.prune_cache()

    @staticmethod
    def prune_cache():
        try:
            files = sorted(CACHE_DIR.glob('*.jpg'), key=lambda p: p.stat().st_mtime, reverse=True)
            size = 0
            for file in files:
                size += file.stat().st_size
                if size > 128 * 1024 * 1024:
                    file.unlink(missing_ok=True)
        except OSError:
            pass
