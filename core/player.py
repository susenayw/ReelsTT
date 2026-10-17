from __future__ import annotations

import gc
import logging
import os
from pathlib import Path
import time

import psutil
from PySide6.QtCore import QObject, QTimer, Signal, Qt
from PySide6.QtWidgets import QStackedWidget, QWidget

from core.config import RESOURCE_DIR

_DLL_HANDLES = []


def load_mpv():
    native = RESOURCE_DIR / 'native'
    os.environ['PATH'] = str(native) + os.pathsep + os.environ.get('PATH', '')
    if hasattr(os, 'add_dll_directory'):
        _DLL_HANDLES.append(os.add_dll_directory(str(native)))
    import mpv
    return mpv


def memory_usage_mb() -> float:
    """Working set of this app plus thumbnail workers, excluding shared GPU VRAM."""
    process = psutil.Process()
    total = process.memory_info().rss
    try:
        for child in process.children(recursive=True):
            try:
                total += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return total / 1_000_000


def committed_memory_mb() -> float:
    process = psutil.Process()
    usage = process.memory_info()
    total = getattr(usage, 'private', usage.rss)
    try:
        for child in process.children(recursive=True):
            try:
                info = child.memory_info()
                total += getattr(info, 'private', info.rss)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return total / 1_000_000


class VideoSurface(QWidget):
    clicked = Signal()
    scrolled = Signal(int)
    swiped = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.setStyleSheet('background: #09080C;')
        self.setMouseTracking(True)
        self._press = None
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.position()

    def mouseReleaseEvent(self, event):
        if self._press is None:
            return
        delta = self._press.y() - event.position().y()
        if abs(delta) > 70:
            self.swiped.emit(1 if delta > 0 else -1)
        elif abs(delta) < 15:
            self.clicked.emit()
        self._press = None

    def wheelEvent(self, event):
        if abs(event.angleDelta().y()) > 10:
            self.scrolled.emit(1 if event.angleDelta().y() < 0 else -1)
        event.accept()


class Slot:
    def __init__(self, surface, player):
        self.surface, self.player = surface, player
        self.path = None
        self.index = -1


class PlayerPool(QObject):
    changed = Signal(int, str)
    position = Signal(float, float)
    playback = Signal(bool)
    media_info = Signal(str)
    error = Signal(str)
    memory = Signal(float, int, str)
    end_of_playlist = Signal()
    native_command = Signal(str)

    def __init__(self, stack: QStackedWidget, parent=None):
        super().__init__(parent)
        self.stack = stack
        self.empty = QWidget()
        self.empty.setStyleSheet('background: #09080C;')
        stack.addWidget(self.empty)
        self.slots: list[Slot] = []
        self.paths = []
        self.index = -1
        self.current = None
        self.volume = 70
        self.muted = False
        self.loop = True
        self._mpv = None
        self._last_scroll = 0.0
        self._ended_handled = False
        self._reported_error = False
        self._last_info = ''
        self._started_at = 0
        self._conserve = False
        self._warning_sent = False
        self.timer = QTimer(self)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self.poll)
        self.memory_timer = QTimer(self)
        self.memory_timer.setInterval(1000)
        self.memory_timer.timeout.connect(self.check_memory)
        self.memory_timer.start()
        self.preloader = QTimer(self)
        self.preloader.setSingleShot(True)
        self.preloader.timeout.connect(self.preload)

    def create_slot(self):
        if self._mpv is None:
            self._mpv = load_mpv()
        surface = VideoSurface()
        self.stack.addWidget(surface)
        surface.clicked.connect(self.toggle_pause)
        surface.scrolled.connect(self.scroll)
        surface.swiped.connect(self.move)
        try:
            player = self._mpv.MPV(
                log_handler=self.mpv_log, loglevel='warn',
                wid=str(int(surface.winId())), vo='gpu', gpu_api='d3d11',
                gpu_dumb_mode=True, swapchain_depth=1, scale='bilinear', cscale='bilinear',
                dscale='bilinear', deband=False, interpolation=False,
                hwdec='auto-safe', input_default_bindings=False, input_vo_keyboard=True,
                osc=False, ytdl=False, config=False, terminal=False, idle=True,
                keep_open=True, force_window=True, pause=True, mute=True,
                cache=False, demuxer_max_bytes='4MiB', demuxer_max_back_bytes='0',
                demuxer_readahead_secs='0.25', vd_lavc_threads=1, hwdec_extra_frames=0,
                audio_buffer='0.15', video_sync='audio',
            )
        except Exception:
            self.stack.removeWidget(surface)
            surface.deleteLater()
            raise
        slot = Slot(surface, player)
        self.slots.append(slot)
        bindings = {'SPACE': 'pause', 'DOWN': 'next', 's': 'next', 'UP': 'previous', 'w': 'previous',
                    'm': 'mute', 'l': 'loop', 'f': 'save', 'e': 'location', 'DEL': 'delete',
                    'ESC': 'back', 'BS': 'back', 'F11': 'fullscreen',
                    'RIGHT': 'seek-forward', 'LEFT': 'seek-back'}
        for key, command in bindings.items():
            def callback(command=command):
                if self.current is slot:
                    self.native_command.emit(command)
            player.on_key_press(key)(callback)
        player.on_key_press('WHEEL_DOWN')(lambda: surface.scrolled.emit(1) if self.current is slot else None)
        player.on_key_press('WHEEL_UP')(lambda: surface.scrolled.emit(-1) if self.current is slot else None)
        pointer = {'y': None}

        @player.key_binding('MBTN_LEFT')
        def mouse(state='p-', *_):
            if self.current is not slot:
                return
            position = player.mouse_pos or {}
            if state[0] == 'd':
                pointer['y'] = position.get('y', 0)
            elif state[0] == 'u':
                delta = (pointer['y'] or 0) - position.get('y', pointer['y'] or 0)
                if abs(delta) > 70:
                    surface.swiped.emit(1 if delta > 0 else -1)
                else:
                    surface.clicked.emit()
                pointer['y'] = None
            elif state[0] == 'p':
                surface.clicked.emit()
        return slot

    @staticmethod
    def mpv_log(level, component, message):
        if level in ('warn', 'error', 'fatal'):
            logging.getLogger('mpv').warning('%s: %s', component, message.rstrip())

    def set_playlist(self, paths: list[str], index=0):
        self.close_media()
        self.paths = paths[:]
        self.index = -1
        self._conserve = False
        self._warning_sent = False
        if self.paths:
            self.show_index(max(0, min(index, len(self.paths) - 1)))

    def load_slot(self, slot, index):
        slot.player.pause = True
        slot.player.mute = True
        slot.player.loop_file = 'no'
        slot.index, slot.path = index, self.paths[index]
        slot.player.command('loadfile', slot.path, 'replace')

    def show_index(self, index):
        if not 0 <= index < len(self.paths):
            self.end_of_playlist.emit()
            return
        old = self.current
        try:
            slot = next((s for s in self.slots if s.path == self.paths[index]), None)
            if slot is None:
                wanted = {self.paths[i] for i in (index-1, index, index+1) if 0 <= i < len(self.paths)}
                reusable = next((s for s in self.slots if s is not old and s.path not in wanted), None)
                if reusable is not None:
                    slot = reusable
                elif len(self.slots) < (1 if self._conserve else 3):
                    slot = self.create_slot()
                else:
                    slot = next((s for s in self.slots if s is not old), old)
                self.load_slot(slot, index)
            if old and old is not slot:
                old.player.pause = True
                old.player.mute = True
                try:
                    old.player.command('seek', 0, 'absolute+exact')
                except Exception:
                    pass
            self.index, self.current = index, slot
            slot.player.volume = self.volume
            slot.player.mute = self.muted
            slot.player.loop_file = 'inf' if self.loop else 'no'
            self.stack.setCurrentWidget(slot.surface)
            slot.player.pause = False
            self._ended_handled = False
            self._reported_error = False
            self._last_info = ''
            self._started_at = time.monotonic()
            self.changed.emit(index, slot.path)
            self.playback.emit(True)
            self.timer.start()
            self.preloader.start(450)
        except Exception as exc:
            logging.exception('Playback failed')
            self.error.emit(f'Unable to start playback: {exc}')

    def preload(self):
        if not self.current or self._conserve or memory_usage_mb() > 360:
            return
        # Next first; only two adjacent files are ever opened in the background.
        wanted = [i for i in (self.index + 1, self.index - 1) if 0 <= i < len(self.paths)]
        for i in wanted:
            if committed_memory_mb() + 100 > 440:
                break
            if memory_usage_mb() > 390:
                self.check_memory()
                break
            if any(s.path == self.paths[i] for s in self.slots):
                continue
            slot = next((s for s in self.slots if s is not self.current and s.path not in
                         [self.paths[j] for j in wanted]), None)
            try:
                if slot is None:
                    if len(self.slots) >= 3:
                        continue
                    slot = self.create_slot()
                self.load_slot(slot, i)
            except Exception:
                logging.exception('Neighbor preload failed')

    def move(self, delta):
        if self.paths:
            self.show_index(self.index + delta)

    def scroll(self, delta):
        now = time.monotonic()
        if now - self._last_scroll > .25:
            self._last_scroll = now
            self.move(delta)

    def toggle_pause(self):
        if self.current:
            paused = not self.current.player.pause
            self.current.player.pause = paused
            self.playback.emit(not paused)

    def seek(self, seconds, absolute=False):
        if self.current:
            try:
                self.current.player.command('seek', seconds, 'absolute+exact' if absolute else 'relative+exact')
            except Exception:
                pass

    def set_volume(self, volume):
        self.volume = max(0, min(100, volume))
        if self.current:
            self.current.player.volume = self.volume

    def set_muted(self, muted):
        self.muted = muted
        if self.current:
            self.current.player.mute = muted

    def set_loop(self, loop):
        self.loop = loop
        if self.current:
            self.current.player.loop_file = 'inf' if loop else 'no'

    def poll(self):
        if not self.current:
            return
        try:
            player = self.current.player
            position, duration = player.time_pos or 0, player.duration or 0
            self.position.emit(float(position), float(duration))
            params = player.video_params
            if params:
                codec = player.video_codec or ''
                hw = player.hwdec_current or 'software'
                info = f'{Path(self.current.path).suffix[1:].upper()}  ·  {params.get("w", "?")} × {params.get("h", "?")}  ·  {codec}  ·  {hw}'
                if info != self._last_info:
                    self._last_info = info
                    self.media_info.emit(info)
            if player.eof_reached and not self.loop and not self._ended_handled:
                self._ended_handled = True
                if self.index + 1 < len(self.paths):
                    self.move(1)
                else:
                    self.playback.emit(False)
            if (time.monotonic() - self._started_at > 6 and not params and
                    not self._reported_error and player.idle_active):
                self._reported_error = True
                self.error.emit('This file could not be opened. It may be unavailable, damaged, or unsupported.')
        except Exception:
            logging.debug('Playback state query failed', exc_info=True)

    def check_memory(self):
        usage = memory_usage_mb()
        committed = committed_memory_mb()
        if self.current and (usage > 390 or committed > 440) and not self._conserve:
            self._conserve = True
            self.preloader.stop()
            for slot in self.slots[:]:
                if slot is not self.current:
                    self.destroy_slot(slot)
            gc.collect()
            usage = memory_usage_mb()
            committed = committed_memory_mb()
        mode = 'Memory saver' if self._conserve else 'Adaptive preload'
        if (usage > 480 or committed > 480) and self.current:
            mode = 'High memory · single player'
            if not self._warning_sent:
                self._warning_sent = True
                self.error.emit(f'Memory pressure: {usage:.0f} MB RAM, {committed:.0f} MB committed. Background players have been released; the active decoder may still exceed the target.')
        self.memory.emit(usage, len(self.slots), mode)

    def destroy_slot(self, slot):
        try:
            slot.player.terminate()
        except Exception:
            logging.exception('Player cleanup failed')
        self.stack.removeWidget(slot.surface)
        slot.surface.deleteLater()
        self.slots.remove(slot)

    def close_media(self):
        self.preloader.stop()
        self.timer.stop()
        self.stack.setCurrentWidget(self.empty)
        self.current = None
        for slot in self.slots[:]:
            self.destroy_slot(slot)
        self.paths = []
        self.index = -1
        gc.collect()

    def release_path(self, path):
        """Close all file handles before sending a playing file to Recycle Bin."""
        if any(s.path == path for s in self.slots):
            self.close_media()
