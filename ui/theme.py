from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ACCENT = '#D0BCFF'
ICONS = {
    'folder': '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10H3Z"/>',
    'bookmark': '<path d="M6 21V4h12v17l-6-4Z"/>',
    'plus': '<path d="M12 5v14M5 12h14"/>',
    'search': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    'grid': '<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>',
    'list': '<path d="M8 5h13M8 12h13M8 19h13M3 5h1M3 12h1M3 19h1"/>',
    'back': '<path d="M19 12H5m6-6-6 6 6 6"/>',
    'play': '<path d="m9 5 11 7-11 7Z"/>',
    'pause': '<path d="M8 5v14M16 5v14"/>',
    'sound': '<path d="M4 9v6h4l5 4V5L8 9Zm13-1a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/>',
    'mute': '<path d="M4 9v6h4l5 4V5L8 9Zm13 0 5 6m0-6-5 6"/>',
    'loop': '<path d="M5 8h13l-3-3m3 3-3 3M19 16H6l3 3m-3-3 3-3M4 13V9a1 1 0 0 1 1-1m15 3v4a1 1 0 0 1-1 1"/>',
    'trash': '<path d="M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7"/>',
    'settings': '<path d="m9 3-1 3-3 1-2 4 2 2v4l4 3 3-1 3 1 4-3v-4l2-2-2-4-3-1-1-3Z"/><circle cx="12" cy="12" r="3"/>',
    'fullscreen': '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>',
    'help': '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 4 3c-1 .5-1 1-1 2m0 3h.01"/>',
    'up': '<path d="m6 14 6-6 6 6"/>',
    'down': '<path d="m6 10 6 6 6-6"/>',
    'refresh': '<path d="M20 7v5h-5M20 12a8 8 0 1 0-2 5"/>',
    'close': '<path d="m6 6 12 12M18 6 6 18"/>',
    'check': '<path d="m5 12 4 4L19 6"/>',
    'more': '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
}


def icon(name, color=ACCENT, size=24):
    body = ICONS.get(name, ICONS['play'])
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    pix = QPixmap(size * 2, size * 2)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    pix.setDevicePixelRatio(2)
    return QIcon(pix)


STYLE = '''
QWidget { background: #141218; color: #F2EEF8; font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow, QDialog { background: #141218; }
QLabel { background: transparent; }
QToolTip { background: #3C304A; color: #EADDFF; border: 1px solid #6B557F; padding: 7px; border-radius: 5px; }
QPushButton { background: #2B2533; border: 1px solid transparent; border-radius: 18px; padding: 10px 16px; color: #D7CDDF; }
QPushButton:hover { background: #393042; }
QPushButton:pressed { background: #4F378B; }
QPushButton:focus { border-color: #A68BCE; }
QPushButton:disabled { color: #696071; background: #201C25; }
QPushButton[primary="true"] { background: #D0BCFF; color: #381E72; font-weight: 600; }
QPushButton[primary="true"]:hover { background: #DFD0FF; }
QPushButton[active="true"] { background: #4F378B; color: #EADDFF; }
QPushButton[tonal="true"] { background: #342A41; color: #D0BCFF; }
QPushButton[iconOnly="true"] { border-radius: 15px; padding: 8px; }
QPushButton[danger="true"] { color: #F2B8B5; }
QFrame#rail { background: #1C1A21; border-right: 1px solid #2C2832; }
QPushButton[nav="true"] { background: transparent; padding: 9px 3px; font-size: 11px; border-radius: 17px; }
QPushButton[nav="true"][active="true"] { background: #494055; color: #EADDFF; }
QFrame#line { background: #2E2835; max-height: 1px; }
QLabel[muted="true"] { color: #978CA4; }
QLabel[eyebrow="true"] { color: #A99ABD; font-size: 10px; font-weight: 600; letter-spacing: 2px; }
QLineEdit { background: #211E27; border: 1px solid #3C3347; border-radius: 21px; padding: 11px 17px; selection-background-color: #4F378B; color: #E9DFF2; }
QLineEdit:focus { border-color: #B097CC; }
QComboBox { background: #211E27; border: 1px solid #3C3347; border-radius: 12px; padding: 8px 12px; min-height: 19px; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: #2B2333; selection-background-color: #4F378B; padding: 7px; border: 1px solid #5B456E; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: #4A4055; border-radius: 3px; min-height: 35px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QSlider::groove:horizontal { background: #46394F; height: 4px; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #D0BCFF; border-radius: 2px; }
QSlider::handle:horizontal { background: #D0BCFF; width: 12px; margin: -4px 0; border-radius: 6px; }
QMenu { background: #302638; border: 1px solid #5B496D; padding: 6px; border-radius: 10px; }
QMenu::item { padding: 10px 18px; border-radius: 6px; }
QMenu::item:selected { background: #4F3B61; }
QMenu::separator { height: 1px; background: #50415C; margin: 5px 10px; }
QDialog QLabel { background: transparent; }
QCheckBox { spacing: 10px; background: transparent; padding: 8px 0; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #9176AD; border-radius: 5px; background: #211A29; }
QCheckBox::indicator:checked { background: #B69AD9; border-color: #D0BCFF; }
QMessageBox { background: #241E2C; }
QFrame#toast { background: #E6DDEF; border-radius: 12px; }
QFrame#toast QLabel { color: #32223F; }
'''
