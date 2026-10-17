from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import threading

from PySide6.QtCore import QThread, Signal

EXTENSIONS = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv', '.wmv', '.ts', '.m2ts',
              '.m4v', '.mpg', '.mpeg', '.mts', '.3gp', '.ogv', '.vob', '.mxf', '.asf'}


@dataclass
class Folder:
    path: str
    videos: list[str] = field(default_factory=list)
    available: bool = True
    warning: str = ''

    @property
    def name(self):
        return Path(self.path).name or self.path


def scan_folder(path: str, recursive=True, cancelled=None) -> Folder:
    folder = Folder(path)
    if not Path(path).is_dir():
        folder.available = False
        folder.warning = 'Folder is unavailable. Reconnect the drive or choose a new location.'
        return folder
    stack = [path]
    while stack:
        if cancelled and cancelled():
            break
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if cancelled and cancelled():
                        break
                    try:
                        if entry.is_file(follow_symlinks=False) and Path(entry.name).suffix.lower() in EXTENSIONS:
                            folder.videos.append(entry.path)
                        elif recursive and entry.is_dir(follow_symlinks=False) and not entry.name.startswith('.'):
                            stack.append(entry.path)
                    except OSError:
                        continue
        except OSError:
            folder.warning = 'Some files or subfolders could not be read.'
    folder.videos.sort(key=lambda p: (Path(p).name.casefold(), p.casefold()))
    return folder


class LibraryScanner(QThread):
    found = Signal(object)
    completed = Signal()

    def __init__(self, paths: list[str], recursive=True, parent=None):
        super().__init__(parent)
        self.paths, self.recursive = paths[:], recursive
        self.cancelled = threading.Event()

    def run(self):
        try:
            for path in self.paths:
                if self.cancelled.is_set():
                    break
                self.found.emit(scan_folder(path, self.recursive, self.cancelled.is_set))
        finally:
            self.completed.emit()

    def cancel(self):
        self.cancelled.set()
