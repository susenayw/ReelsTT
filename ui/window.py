from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import subprocess
import time

from PySide6.QtCore import Qt, QTimer, QEvent, QSize
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QPixmapCache, QDesktopServices, QIcon
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel, QVBoxLayout,
    QHBoxLayout, QGridLayout, QStackedWidget, QScrollArea, QLineEdit, QComboBox,
    QSlider, QFileDialog, QMenu, QDialog, QCheckBox, QMessageBox, QSizePolicy)

from core.config import APP_DIR, DATA_DIR, RESOURCE_DIR, Config
from core.version import __version__, REPOSITORY_URL
from core.library import Folder, LibraryScanner
from core.player import PlayerPool, memory_usage_mb, committed_memory_mb
from core.thumbnails import ThumbnailWorker, cache_path
from ui.theme import icon
from ui.widgets import (label, button, active, Brand, NavButton, HeroArt, FolderCard,
                        AddCard, VolumeButton, ActionButton, SeekSlider, Toast)


class MainWindow(QMainWindow):
    def __init__(self, config: Config, initial_folder=None, diagnostics=False):
        super().__init__()
        self.config = config
        self.setWindowTitle(f'ReelsTT {__version__} — Your videos, your flow')
        self.setWindowIcon(QIcon(str(RESOURCE_DIR / 'assets' / 'reelstt.ico')))
        self.setMinimumSize(850, 640)
        size = config.get('window', [1280, 870])
        available = QApplication.primaryScreen().availableGeometry()
        self.resize(max(850, min(size[0], available.width()-24)), max(640, min(size[1], available.height()-45)))
        self.setAcceptDrops(True)
        self.folders: dict[str, Folder] = {}
        self.cards: dict[str, FolderCard] = {}
        self.scanner = None
        self.saved_mode = False
        self.feed_active = False
        self.current_folder = None
        self.playlist = []
        self.current_path = ''
        self.duration = 0
        self._columns = 0
        self._render_limit = 120
        self._refresh_pending = False
        self._was_maximized = False
        self._diagnostics = diagnostics
        self._peak_memory = 0.0
        self._startup = time.monotonic()
        QPixmapCache.setCacheLimit(16 * 1024)
        self.build_ui()
        self.pool = PlayerPool(self.video_stack, self)
        self.pool.volume = self.config.get('volume', 70)
        self.pool.muted = self.config.get('muted', False)
        self.pool.loop = self.config.get('loop', True)
        self.pool.changed.connect(self.on_video_changed)
        self.pool.position.connect(self.on_position)
        self.pool.playback.connect(self.on_playback)
        self.pool.media_info.connect(self.media_info.setText)
        self.pool.error.connect(self.playback_error)
        self.pool.memory.connect(self.on_memory)
        self.pool.end_of_playlist.connect(lambda: self.toast('You’ve reached the edge of this collection.'))
        self.pool.native_command.connect(self.native_command)
        self.thumbnails = ThumbnailWorker(self)
        self.thumbnails.ready.connect(self.on_thumbnail)
        self.thumbnails.start()
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.reflow)
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self.render_cards)
        self.search.textChanged.connect(lambda: self.render_timer.start(130))
        QApplication.instance().installEventFilter(self)
        if initial_folder:
            self.config.add_folder(initial_folder)
        self.update_nav()
        QTimer.singleShot(100, self.rescan)

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        rail = QFrame()
        rail.setObjectName('rail')
        rail.setFixedWidth(86)
        nav = QVBoxLayout(rail)
        nav.setContentsMargins(8, 22, 8, 18)
        nav.setSpacing(12)
        nav.addWidget(Brand(), 0, Qt.AlignmentFlag.AlignHCenter)
        nav.addSpacing(17)
        nav.addWidget(button('', 'plus', self.add_folder, True, 'Add a video folder', (52, 52)), 0, Qt.AlignmentFlag.AlignHCenter)
        nav.addSpacing(9)
        self.folders_nav = NavButton('Folders', 'folder', lambda: self.show_library(False))
        self.saved_nav = NavButton('Saved', 'bookmark', lambda: self.show_library(True))
        nav.addWidget(self.folders_nav)
        nav.addWidget(self.saved_nav)
        nav.addStretch()
        nav.addWidget(button('', 'help', self.show_help, tooltip='Keyboard shortcuts', size=(40, 40)), 0, Qt.AlignmentFlag.AlignHCenter)
        nav.addWidget(button('', 'settings', self.show_settings, tooltip='Preferences', size=(40, 40)), 0, Qt.AlignmentFlag.AlignHCenter)
        avatar = label('S', 10, '#DED0EC')
        avatar.setFixedSize(30, 30)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet('background: #42384D; border-radius: 15px; color: #DED0EC;')
        nav.addWidget(avatar, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addWidget(rail)
        self.pages = QStackedWidget()
        outer.addWidget(self.pages, 1)
        self.build_library()
        self.build_feed()
        self.snackbar = Toast(root)

    def build_library(self):
        self.library_page = QWidget()
        self.pages.addWidget(self.library_page)
        layout = QVBoxLayout(self.library_page)
        layout.setContentsMargins(42, 0, 42, 18)
        layout.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(0, 22, 0, 22)
        header.addWidget(label('ReelFlow', 19, '#F2EEF8', True))
        header.addSpacing(17)
        header.addWidget(label('│   YOUR VIDEOS. YOUR FLOW.', 8, '#81758E'))
        header.addStretch()
        header.addWidget(label('●  All local. All yours.', 9, '#B5A9C0'))
        header.addSpacing(15)
        header.addWidget(button('', 'help', self.show_help, tooltip='Keyboard shortcuts', size=(34, 34)))
        layout.addLayout(header)
        line = QFrame()
        line.setObjectName('line')
        line.setFixedHeight(1)
        layout.addWidget(line)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.library_scroll = scroll
        body = QWidget()
        scroll.setWidget(body)
        content = QVBoxLayout(body)
        content.setContentsMargins(0, 0, 7, 0)
        content.setSpacing(0)
        hero = QHBoxLayout()
        hero.setContentsMargins(0, 32, 15, 29)
        copy = QVBoxLayout()
        copy.setSpacing(12)
        eye = label('YOUR PERSONAL VIDEO SPACE', 8, '#A99ABD', True)
        eye.setProperty('eyebrow', True)
        copy.addWidget(eye)
        self.hero_title = QLabel()
        self.hero_title.setTextFormat(Qt.TextFormat.RichText)
        self.hero_title.setStyleSheet('font-size: 35px; font-weight: 600; background: transparent;')
        copy.addWidget(self.hero_title)
        self.hero_subtitle = label('', 10, '#A39AAE')
        copy.addWidget(self.hero_subtitle)
        hero.addLayout(copy, 1)
        self.hero_art = HeroArt()
        hero.addWidget(self.hero_art)
        content.addLayout(hero)
        heading = QHBoxLayout()
        text = QVBoxLayout()
        self.section_title = label('', 16, '#F0E9F6', True)
        self.section_subtitle = label('', 9, '#978AA5')
        text.addWidget(self.section_title)
        text.addWidget(self.section_subtitle)
        heading.addLayout(text)
        heading.addStretch()
        heading.addWidget(button(' Add folder', 'plus', self.add_folder, True))
        content.addLayout(heading)
        content.addSpacing(23)
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Find a folder…')
        self.search.setAccessibleName('Find a folder')
        self.search.addAction(icon('search', '#A092B0', 17), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setMaximumWidth(380)
        self.search.setMinimumWidth(220)
        toolbar.addWidget(self.search, 1)
        toolbar.addStretch()
        self.sort = QComboBox()
        for text, key in [('Recently added', 'recent'), ('Name A–Z', 'name'), ('Video count', 'count')]:
            self.sort.addItem(text, key)
        self.sort.setCurrentIndex(max(0, self.sort.findData(self.config.get('sort', 'recent'))))
        self.sort.setAccessibleName('Sort folders')
        self.sort.currentIndexChanged.connect(self.sort_changed)
        toolbar.addWidget(self.sort)
        toolbar.addSpacing(8)
        self.grid_button = button('', 'grid', lambda: self.set_view('grid'), tooltip='Grid view', size=(36, 36))
        self.list_button = button('', 'list', lambda: self.set_view('list'), tooltip='List view', size=(36, 36))
        toolbar.addWidget(self.grid_button)
        toolbar.addWidget(self.list_button)
        toolbar.addWidget(button('', 'refresh', self.rescan, tooltip='Refresh folders (Ctrl+R)', size=(36, 36)))
        content.addLayout(toolbar)
        content.addSpacing(22)
        self.grid_host = QWidget()
        self.grid_layout = QGridLayout(self.grid_host)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(20)
        self.grid_layout.setVerticalSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content.addWidget(self.grid_host)
        self.empty_message = label('', 12, '#AA9BB9')
        self.empty_message.setWordWrap(True)
        self.empty_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_message.setContentsMargins(30, 36, 30, 36)
        content.addWidget(self.empty_message)
        self.load_more = button('Show more', 'plus', self.show_more)
        content.addWidget(self.load_more, 0, Qt.AlignmentFlag.AlignHCenter)
        counts = QHBoxLayout()
        counts.setContentsMargins(0, 21, 0, 19)
        self.library_count = label('', 9, '#92829F')
        counts.addWidget(self.library_count)
        counts.addStretch()
        counts.addWidget(label('Good things deserve a replay.', 9, '#81748F'))
        content.addLayout(counts)
        content.addStretch()
        layout.addWidget(scroll, 1)
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 15, 0, 0)
        footer.addWidget(label('Made for your offline moments.', 8, '#75677F'))
        footer.addStretch()
        self.library_ram = label('', 8, '#92839F')
        footer.addWidget(self.library_ram)
        footer.addSpacing(17)
        footer.addWidget(label(f'REELSTT  /  {__version__} PREVIEW', 8, '#A08CB3'))
        layout.addLayout(footer)
        self.set_view(self.config.get('view', 'grid'), render=False)

    def build_feed(self):
        self.feed_page = QWidget()
        self.pages.addWidget(self.feed_page)
        layout = QVBoxLayout(self.feed_page)
        layout.setContentsMargins(28, 20, 28, 12)
        layout.setSpacing(15)
        top = QHBoxLayout()
        top.addWidget(button(' Library', 'back', lambda: self.show_library(self.saved_mode), tooltip='Return to library (Esc)'))
        top.addStretch()
        self.feed_folder = label('', 10, '#B7A6C7')
        top.addWidget(self.feed_folder)
        top.addStretch()
        top.addWidget(button('', 'fullscreen', self.toggle_fullscreen, tooltip='Fullscreen (F11)', size=(38, 38)))
        layout.addLayout(top)
        middle = QHBoxLayout()
        middle.setSpacing(18)
        self.video_stack = QStackedWidget()
        self.video_stack.setStyleSheet('background: #09080C; border: none;')
        self.video_stack.setMinimumSize(320, 210)
        middle.addWidget(self.video_stack, 1)
        actions = QVBoxLayout()
        actions.setSpacing(15)
        actions.addStretch()
        self.mute_button = VolumeButton()
        self.mute_button.setFixedSize(62, 58)
        self.mute_button.setText('Sound')
        self.mute_button.setIcon(icon('sound'))
        self.mute_button.setToolTip('Mute (M) · Scroll here to adjust volume')
        self.mute_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mute_button.clicked.connect(self.toggle_mute)
        self.mute_button.adjusted.connect(lambda n: self.change_volume(self.volume.value()+n))
        actions.addWidget(self.mute_button)
        self.loop_button = ActionButton('Loop', 'loop', self.toggle_loop, 'Loop current video (L)')
        self.favorite_button = ActionButton('Save', 'bookmark', self.toggle_favorite, 'Save favorite (F)')
        self.location_button = button('', 'folder', self.open_location, tooltip='Open file location (E)', size=(62, 53))
        self.delete_button = button('', 'trash', self.delete_video, tooltip='Move video to Recycle Bin (Delete)', size=(62, 53))
        self.delete_button.setProperty('danger', True)
        self.delete_button.setIcon(icon('trash', '#F2B8B5'))
        for b in (self.loop_button, self.favorite_button, self.location_button, self.delete_button):
            actions.addWidget(b)
        actions.addStretch()
        middle.addLayout(actions)
        layout.addLayout(middle, 1)
        info = QHBoxLayout()
        names = QVBoxLayout()
        names.setSpacing(5)
        self.filename = label('', 16, '#F0E8F8', True)
        self.filename.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.media_info = label('Opening video…', 9, '#A893BA')
        self.media_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        names.addWidget(self.filename)
        names.addWidget(self.media_info)
        info.addLayout(names, 1)
        self.paused_label = label('', 10, '#D0BCFF')
        info.addWidget(self.paused_label)
        layout.addLayout(info)
        self.scrubber = SeekSlider(Qt.Orientation.Horizontal)
        self.scrubber.setRange(0, 10000)
        self.scrubber.setAccessibleName('Video progress')
        self.scrubber.sliderReleased.connect(self.seek_from_slider)
        self.scrubber.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.scrubber)
        controls = QHBoxLayout()
        self.play_button = button('', 'pause', self.toggle_pause, tooltip='Play / pause (Space)', size=(35, 35))
        controls.addWidget(self.play_button)
        self.time_label = label('00:00 / 00:00', 9, '#C9BBD5')
        self.time_label.setMinimumWidth(105)
        controls.addWidget(self.time_label)
        controls.addStretch()
        self.feed_status = label('', 8, '#9F8FB1')
        controls.addWidget(self.feed_status)
        controls.addStretch()
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(self.config.get('volume', 70))
        self.volume.setFixedWidth(85)
        self.volume.setAccessibleName('Volume')
        self.volume.valueChanged.connect(self.change_volume)
        self.volume.sliderReleased.connect(lambda: self.config.set('volume', self.volume.value()))
        controls.addWidget(self.volume)
        controls.addWidget(button('', 'up', lambda: self.pool.move(-1), tooltip='Previous video (↑)', size=(35, 35)))
        self.feed_index = label('', 9, '#C9B8DA')
        controls.addWidget(self.feed_index)
        controls.addWidget(button('', 'down', lambda: self.pool.move(1), tooltip='Next video (↓)', size=(35, 35)))
        layout.addLayout(controls)

    def update_nav(self):
        self.folders_nav.selected = not self.saved_mode
        self.saved_nav.selected = self.saved_mode
        self.folders_nav.update()
        self.saved_nav.update()
        if self.saved_mode:
            self.hero_title.setText('The ones you love.<br>Always <span style="color:#D0BCFF">within reach.</span>')
            self.hero_subtitle.setText('A home for the moments you come back to.')
            self.section_subtitle.setText('Your favorites, collected across every folder.')
            self.search.setPlaceholderText('Find a saved video…')
        else:
            self.hero_title.setText('A little less searching.<br>A lot more <span style="color:#D0BCFF">watching.</span>')
            self.hero_subtitle.setText('All your favorite folders, ready to roll.')
            self.section_subtitle.setText('A collection of moments worth keeping.')
            self.search.setPlaceholderText('Find a folder…')

    def toast(self, text, duration=3800):
        self.snackbar.show_message(text, duration)

    def add_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Add a video folder', str(Path.home() / 'Videos'))
        if path:
            self.add_path(path)

    def add_path(self, path):
        if self.config.add_folder(path):
            self.show_library(False)
            self.rescan()
            self.toast('Folder added. Finding your videos…')
        else:
            self.toast('That folder is already in your library.')

    def rescan(self):
        if self.scanner and self.scanner.isRunning():
            self._refresh_pending = True
            return
        if self.scanner:
            self.scanner.deleteLater()
        paths = self.config.get('folders', [])
        self.folders = {p: self.folders.get(p, Folder(p)) for p in paths}
        self.scanner = LibraryScanner(paths, self.config.get('recursive', True), self)
        self.scanner.found.connect(self.folder_found)
        self.scanner.completed.connect(self.scan_completed)
        self.scanner.start()
        self.section_subtitle.setText('Finding your videos…')
        self.render_cards()

    def folder_found(self, folder):
        if folder.path not in self.config.get('folders', []):
            return
        self.folders[folder.path] = folder
        self.render_timer.start(80)

    def scan_completed(self):
        self.update_nav()
        self.render_timer.start(30)
        if self._refresh_pending:
            self._refresh_pending = False
            QTimer.singleShot(100, self.rescan)

    def sort_changed(self):
        self.config.set('sort', self.sort.currentData())
        self.render_cards()

    def set_view(self, mode, render=True):
        self.config.set('view', mode)
        active(self.grid_button, mode == 'grid')
        active(self.list_button, mode == 'list')
        self._columns = 0
        if render and hasattr(self, 'thumbnails'):
            self.render_cards()

    def render_cards(self):
        if not hasattr(self, 'thumbnails') or self.feed_active:
            return
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()
        query = self.search.text().casefold().strip()
        sort = self.sort.currentData()
        self._grid_widgets = []
        if self.saved_mode:
            favorites = self.config.get('favorites', [])
            items = [p for p in favorites if query in (Path(p).name+' '+p).casefold()]
            if sort == 'name':
                items.sort(key=lambda p: Path(p).name.casefold())
            else:
                items.reverse()
            self.section_title.setText(f'Saved videos   {len(favorites)}')
            for path in items[:self._render_limit]:
                card = FolderCard(path, Path(path).name, str(Path(path).parent), 1, saved=True)
                card.opened.connect(self.open_saved)
                self.cards[path] = card
                self._grid_widgets.append(card)
                self.assign_thumbnail(card, path)
            self.library_count.setText(f'●  {len(favorites):,} saved videos')
        else:
            items = [self.folders.get(p, Folder(p)) for p in self.config.get('folders', [])]
            total = len(items)
            items = [f for f in items if query in (f.name+' '+f.path).casefold()]
            if sort == 'name':
                items.sort(key=lambda f: f.name.casefold())
            elif sort == 'count':
                items.sort(key=lambda f: len(f.videos), reverse=True)
            self.section_title.setText(f'Your folders   {total}')
            for folder in items[:self._render_limit]:
                card = FolderCard(folder.path, folder.name, folder.path, len(folder.videos), available=folder.available)
                card.opened.connect(self.open_folder)
                card.menu_requested.connect(self.folder_menu)
                self.cards[folder.path] = card
                self._grid_widgets.append(card)
                if folder.videos:
                    self.assign_thumbnail(card, folder.videos[0])
            if not query:
                self._grid_widgets.append(AddCard(self.add_folder))
            videos = sum(len(f.videos) for f in self.folders.values())
            self.library_count.setText(f'●  {total:,} folders · {videos:,} videos')
        self.empty_message.setVisible(not items)
        if not items:
            self.empty_message.setText('No matches. Try a different name.' if query else
                ('Your best moments belong here.\nPress F while watching to save a video.' if self.saved_mode else
                 'Your next favorite moment is already on your drive.\nAdd a video folder, or drop one here to begin.'))
        self.load_more.setVisible(len(items) > self._render_limit)
        self._columns = 0
        self.reflow()

    def show_more(self):
        self._render_limit += 120
        self.render_cards()

    def assign_thumbnail(self, card, path):
        card.media_path = path
        thumb = cache_path(path)
        if thumb.exists():
            card.set_cover(str(thumb))
        else:
            self.thumbnails.request(path)

    def on_thumbnail(self, path, target):
        for card in self.cards.values():
            if getattr(card, 'media_path', None) == path:
                card.set_cover(target)

    def reflow(self):
        if not hasattr(self, '_grid_widgets'):
            return
        is_list = self.config.get('view') == 'list'
        columns = 1 if is_list else max(1, min(5, (self.grid_host.width()+20)//270))
        self.hero_art.setVisible(self.width() >= 1050)
        if columns == self._columns:
            return
        self._columns = columns
        while self.grid_layout.count():
            self.grid_layout.takeAt(0)
        for col in range(6):
            self.grid_layout.setColumnStretch(col, 1 if col < columns else 0)
            self.grid_layout.setColumnMinimumWidth(col, 0)
        for i, widget in enumerate(self._grid_widgets):
            if isinstance(widget, FolderCard):
                widget.set_list_mode(is_list)
            else:
                widget.setFixedHeight(130 if is_list else 230)
            self.grid_layout.addWidget(widget, i//columns, i%columns)

    def folder_menu(self, path, position):
        menu = QMenu(self)
        menu.addAction(icon('folder'), 'Open in Explorer', lambda: self.reveal_folder(path))
        menu.addAction(icon('refresh'), 'Refresh folders', self.rescan)
        menu.addSeparator()
        menu.addAction('Remove folder from library', lambda: self.remove_folder(path))
        menu.exec(position)

    def remove_folder(self, path):
        self.config.set('folders', [p for p in self.config.get('folders', []) if p != path])
        self.folders.pop(path, None)
        self.render_cards()
        self.toast('Folder removed from library. Original files kept.')

    def reveal_folder(self, path):
        if Path(path).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.toast('Folder unavailable. Reconnect the drive and refresh.')

    def open_folder(self, path):
        folder = self.folders.get(path)
        if not folder or not folder.available:
            self.toast('This folder is unavailable. Reconnect the drive and refresh.')
            return
        if not folder.videos:
            self.toast('No videos found. Add video files, then refresh this folder.')
            return
        self.current_folder = folder
        self.start_feed(folder.videos, 0)

    def open_saved(self, path):
        paths = [p for p in self.config.get('favorites', []) if Path(p).is_file()]
        if path not in paths:
            self.toast('This saved video is unavailable. Reconnect its drive or restore the file.')
            return
        self.current_folder = None
        self.start_feed(paths, paths.index(path))

    def start_feed(self, paths, index):
        # Stop thumbnail subprocess before starting decoder allocations.
        self.thumbnails.pause(True)
        self.feed_active = True
        self.playlist = paths[:]
        self.pages.setCurrentWidget(self.feed_page)
        active(self.loop_button, self.config.get('loop', True))
        self.update_mute()
        self.pool.set_playlist(self.playlist, index)

    def show_library(self, saved=False):
        if hasattr(self, 'pool'):
            self.pool.close_media()
        self.feed_active = False
        self.current_path = ''
        self.saved_mode = saved
        self._render_limit = 120
        self.search.clear()
        self.pages.setCurrentWidget(self.library_page)
        self.update_nav()
        if hasattr(self, 'thumbnails'):
            self.thumbnails.pause(False)
            self.render_cards()
        if self.isFullScreen():
            self.toggle_fullscreen()

    def on_video_changed(self, index, path):
        self.current_path = path
        self.filename.setText(Path(path).name)
        self.filename.setToolTip(path)
        self.media_info.setText('Opening video…')
        self.feed_folder.setText(f'{self.current_folder.name if self.current_folder else "Saved videos"}  ·  {index+1:,} / {len(self.pool.paths):,}')
        self.feed_index.setText(f'{index+1:02} / {len(self.pool.paths):02}')
        self.scrubber.setValue(0)
        self.time_label.setText('00:00 / 00:00')
        self.update_favorite()

    @staticmethod
    def timestamp(seconds):
        seconds = int(max(0, seconds))
        if seconds >= 3600:
            return f'{seconds//3600:d}:{seconds//60%60:02d}:{seconds%60:02d}'
        return f'{seconds//60:02d}:{seconds%60:02d}'

    def on_position(self, position, duration):
        self.duration = duration
        if not self.scrubber.isSliderDown():
            self.scrubber.setValue(int(position/duration*10000) if duration else 0)
        self.time_label.setText(f'{self.timestamp(position)} / {self.timestamp(duration)}')

    def seek_from_slider(self):
        if self.duration:
            self.pool.seek(self.scrubber.value()/10000*self.duration, True)

    def toggle_pause(self):
        self.pool.toggle_pause()

    def on_playback(self, playing):
        self.play_button.setIcon(icon('pause' if playing else 'play'))
        self.paused_label.setText('' if playing else 'Paused  ·  Space to resume')

    def change_volume(self, value):
        value = max(0, min(100, value))
        if self.volume.value() != value:
            self.volume.blockSignals(True)
            self.volume.setValue(value)
            self.volume.blockSignals(False)
        if hasattr(self, 'pool'):
            self.pool.set_volume(value)
            self.pool.set_muted(False)
        self.config.data['volume'] = value
        self.config.data['muted'] = False
        self.update_mute()

    def toggle_mute(self):
        value = not self.config.get('muted', False)
        self.config.set('muted', value)
        self.pool.set_muted(value)
        self.update_mute()

    def update_mute(self):
        muted = self.config.get('muted', False)
        self.mute_button.setIcon(icon('mute' if muted else 'sound'))
        self.mute_button.setText('Muted' if muted else 'Sound')
        active(self.mute_button, muted)

    def toggle_loop(self):
        value = not self.config.get('loop', True)
        self.config.set('loop', value)
        self.pool.set_loop(value)
        active(self.loop_button, value)
        self.toast('Loop on. Stay in the moment.' if value else 'Loop off. The next video plays automatically.')

    def toggle_favorite(self):
        if not self.current_path:
            return
        saved = self.config.toggle_favorite(self.current_path)
        self.update_favorite()
        self.toast('Added to your saved videos.' if saved else 'Removed from saved videos.')

    def update_favorite(self):
        saved = self.current_path in self.config.get('favorites', [])
        active(self.favorite_button, saved)
        self.favorite_button.setText('Saved' if saved else 'Save')

    def open_location(self):
        if self.current_path and Path(self.current_path).exists():
            # One properly quoted Explorer argument; paths never enter a shell.
            subprocess.Popen(['explorer.exe', '/select,', str(Path(self.current_path))])
        else:
            self.toast('The original file is unavailable.')

    def delete_video(self):
        if not self.current_path:
            return
        path = self.current_path
        player = self.pool.current
        was_paused = bool(player.player.pause) if player else True
        if player:
            player.player.pause = True
        result = QMessageBox.question(self, 'Move to Recycle Bin?',
            f'{Path(path).name}\n\nMove this video to the Windows Recycle Bin? You can restore it from there.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel)
        if result != QMessageBox.StandardButton.Yes:
            if self.pool.current:
                self.pool.current.player.pause = was_paused
            return
        index = self.pool.index
        paths = self.pool.paths[:]
        self.pool.release_path(path)
        try:
            from send2trash import send2trash
            send2trash(path)
        except Exception as exc:
            logging.exception('Recycle Bin operation failed')
            self.pool.set_playlist(paths, index)
            self.toast(f'Could not move file to Recycle Bin: {exc}', 7000)
            return
        for folder in self.folders.values():
            folder.videos = [p for p in folder.videos if p != path]
        favorites = self.config.get('favorites', [])
        if path in favorites:
            favorites.remove(path)
            self.config.save()
        paths = [p for p in paths if p != path]
        self.playlist = paths
        if paths:
            self.pool.set_playlist(paths, min(index, len(paths)-1))
        else:
            self.show_library(self.saved_mode)
        self.toast('Moved to Recycle Bin. You can restore it in Windows.')

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized() if self._was_maximized else self.showNormal()
        else:
            self._was_maximized = self.isMaximized()
            self.showFullScreen()

    def native_command(self, command):
        if not self.feed_active or QApplication.activeModalWidget() is not None:
            return
        commands = {'pause': self.toggle_pause, 'next': lambda: self.pool.move(1),
                    'previous': lambda: self.pool.move(-1), 'mute': self.toggle_mute,
                    'loop': self.toggle_loop, 'save': self.toggle_favorite,
                    'location': self.open_location, 'delete': self.delete_video,
                    'back': lambda: self.show_library(self.saved_mode),
                    'fullscreen': self.toggle_fullscreen,
                    'seek-forward': lambda: self.pool.seek(5), 'seek-back': lambda: self.pool.seek(-5)}
        if command in commands:
            commands[command]()

    def playback_error(self, message):
        self.toast(message, 8000)
        logging.warning(message)
        if self.feed_active and self.media_info.text() == 'Opening video…':
            self.media_info.setText('Unable to open this video. Use ↓ to continue, or Esc for the library.')

    def on_memory(self, usage, players, mode):
        self._peak_memory = max(self._peak_memory, usage)
        self.library_ram.setText(f'{usage:.0f} MB RAM')
        self.feed_status.setText(f'{usage:.0f} MB RAM  ·  {players} player{"s" if players != 1 else ""}  ·  {mode}')
        if self._diagnostics:
            state = {'pid': os.getpid(), 'ram_mb': round(usage, 2), 'peak_ram_mb': round(self._peak_memory, 2),
                     'committed_mb': round(committed_memory_mb(), 2),
                     'players': players, 'mode': mode, 'feed': self.feed_active,
                     'index': self.pool.index, 'path': self.current_path,
                     'time': round(time.monotonic()-self._startup, 2),
                     'folders': len(self.folders), 'videos': sum(len(f.videos) for f in self.folders.values())}
            if self.pool.current:
                try:
                    state['hwdec'] = self.pool.current.player.hwdec_current
                    state['position'] = self.pool.current.player.time_pos
                    state['duration'] = self.pool.current.player.duration
                    state['paused'] = self.pool.current.player.pause
                except Exception:
                    pass
            try:
                target = DATA_DIR / 'runtime.json'
                temp = target.with_suffix('.tmp')
                temp.write_text(json.dumps(state, indent=2), encoding='utf-8')
                temp.replace(target)
            except OSError:
                pass

    def show_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Find your flow — keyboard shortcuts')
        dialog.setMinimumWidth(450)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(label('Find your flow', 19, '#EBDDFA', True))
        layout.addSpacing(12)
        shortcuts = [('Next / previous video', '↓ / ↑  or  S / W'), ('Play / pause', 'Space'),
                     ('Seek 5 seconds', '→ / ←'), ('Mute sound', 'M'), ('Loop current video', 'L'),
                     ('Save a favorite', 'F'), ('Open file location', 'E'), ('Move to Recycle Bin', 'Delete'),
                     ('Return to library', 'Esc / Backspace'), ('Fullscreen', 'F11'),
                     ('Search / refresh library', '/  /  Ctrl+R'), ('Add folder', 'Ctrl+O')]
        for text, key in shortcuts:
            row = QHBoxLayout()
            row.addWidget(label(text, 10, '#B8A7C7'))
            row.addStretch()
            row.addWidget(label(key, 10, '#D0BCFF'))
            layout.addLayout(row)
            layout.addSpacing(5)
        layout.addSpacing(15)
        layout.addWidget(button('Got it', callback=dialog.accept, primary=True))
        dialog.exec()

    def show_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('ReelsTT preferences')
        dialog.setMinimumWidth(470)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 25, 28, 25)
        layout.addWidget(label('Make yourself at home', 19, '#EBDDFA', True))
        layout.addWidget(label(f'ReelsTT {__version__} · Prerelease', 10, '#A99ABD'))
        layout.addSpacing(15)
        repeat = QCheckBox('Loop the current video')
        repeat.setChecked(self.config.get('loop', True))
        recursive = QCheckBox('Include videos in subfolders')
        recursive.setChecked(self.config.get('recursive', True))
        layout.addWidget(repeat)
        layout.addWidget(recursive)
        note = label('Memory target: under 500 MB RAM. Neighboring videos are preloaded while memory permits. At high usage, the app releases background players. Demanding decoders may exceed the target. GPU memory is separate.\n\nFolders, favorites, and settings stay on this device.', 10, '#9D8AAD')
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addSpacing(14)
        layout.addWidget(button('Open app data folder', 'folder', lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(DATA_DIR)))))
        layout.addWidget(button('View releases on GitHub', 'folder', lambda: QDesktopServices.openUrl(QUrl(REPOSITORY_URL + '/releases'))))
        layout.addWidget(button('Save preferences', callback=dialog.accept, primary=True))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            changed = recursive.isChecked() != self.config.get('recursive', True)
            self.config.data['recursive'] = recursive.isChecked()
            self.config.data['loop'] = repeat.isChecked()
            self.config.save()
            self.pool.set_loop(repeat.isChecked())
            active(self.loop_button, repeat.isChecked())
            if changed:
                self.rescan()
            self.toast('Preferences saved.')

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress and QApplication.activeWindow() is self:
            if QApplication.activeModalWidget() is not None:
                return False
            focus = QApplication.focusWidget()
            if isinstance(focus, (QLineEdit, QComboBox)):
                if event.key() == Qt.Key.Key_Escape:
                    focus.clearFocus()
                    return True
                return False
            key = event.key()
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                if key == Qt.Key.Key_O:
                    self.add_folder()
                    return True
                if key == Qt.Key.Key_R:
                    self.rescan()
                    return True
                return False
            if event.isAutoRepeat() and key in (Qt.Key.Key_Delete, Qt.Key.Key_F, Qt.Key.Key_L, Qt.Key.Key_M):
                return True
            if key == Qt.Key.Key_F11:
                self.toggle_fullscreen()
                return True
            if not self.feed_active and key == Qt.Key.Key_Slash:
                self.search.setFocus()
                return True
            if self.feed_active:
                actions = {Qt.Key.Key_Down: lambda: self.pool.move(1), Qt.Key.Key_S: lambda: self.pool.move(1),
                    Qt.Key.Key_Up: lambda: self.pool.move(-1), Qt.Key.Key_W: lambda: self.pool.move(-1),
                    Qt.Key.Key_Space: self.toggle_pause, Qt.Key.Key_M: self.toggle_mute,
                    Qt.Key.Key_L: self.toggle_loop, Qt.Key.Key_F: self.toggle_favorite,
                    Qt.Key.Key_E: self.open_location, Qt.Key.Key_Delete: self.delete_video,
                    Qt.Key.Key_Escape: lambda: self.show_library(self.saved_mode),
                    Qt.Key.Key_Backspace: lambda: self.show_library(self.saved_mode),
                    Qt.Key.Key_Left: lambda: self.pool.seek(-5), Qt.Key.Key_Right: lambda: self.pool.seek(5)}
                if key in actions:
                    if not event.isAutoRepeat() or key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                        actions[key]()
                    return True
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'resize_timer'):
            self.resize_timer.start(100)
        if hasattr(self, 'snackbar'):
            self.snackbar.reposition()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and any(Path(u.toLocalFile()).is_dir() for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        added = False
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).is_dir():
                added = self.config.add_folder(path) or added
        if added:
            self.show_library(False)
            self.rescan()
            self.toast('Folders added. Finding your videos…')
        event.acceptProposedAction()

    def closeEvent(self, event: QCloseEvent):
        self.pool.close_media()
        self.pool.memory_timer.stop()
        self.thumbnails.shutdown()
        if self.scanner and self.scanner.isRunning():
            self.scanner.cancel()
            if not self.scanner.wait(5000):
                event.ignore()
                self.toast('Waiting for the drive to finish responding. Try closing again in a moment.', 7000)
                return
        if not self.isMaximized() and not self.isFullScreen():
            self.config.data['window'] = [self.width(), self.height()]
        self.config.save()
        event.accept()
