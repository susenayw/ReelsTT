from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QSize, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QLinearGradient, QPixmap, QImageReader, QPen
from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QFrame, QHBoxLayout, QVBoxLayout, QSlider

from ui.theme import icon


def label(text='', size=13, color=None, bold=False, parent=None):
    result = QLabel(text, parent)
    result.setTextFormat(Qt.TextFormat.PlainText)
    font = QFont('Segoe UI', size)
    font.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
    result.setFont(font)
    if color:
        result.setStyleSheet(f'color: {color}; background: transparent;')
    return result


def button(text='', glyph=None, callback=None, primary=False, tooltip='', size=None):
    result = QPushButton(text)
    result.setCursor(Qt.CursorShape.PointingHandCursor)
    result.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    if glyph:
        result.setIcon(icon(glyph, '#381E72' if primary else '#D0BCFF'))
        result.setIconSize(QSize(19, 19))
    if primary:
        result.setProperty('primary', True)
    if size:
        result.setFixedSize(*size)
    result.setToolTip(tooltip)
    result.setAccessibleName(tooltip or text)
    if callback:
        result.clicked.connect(callback)
    return result


def active(widget, value):
    widget.setProperty('active', value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class Brand(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 44)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.translate(10, 7)
        p.shear(-.20, 0)
        p.setBrush(QColor('#D0BCFF'))
        p.drawRoundedRect(QRectF(0, 0, 11, 29), 4, 4)
        p.setBrush(QColor('#A78ADE'))
        p.drawRoundedRect(QRectF(16, 9, 11, 20), 4, 4)


class NavButton(QPushButton):
    def __init__(self, title, glyph, callback):
        super().__init__()
        self.title, self.glyph, self.selected = title, glyph, False
        self.setFixedSize(68, 65)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(title)
        self.setToolTip(title)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.clicked.connect(callback)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.selected or self.underMouse():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor('#494055' if self.selected else '#2B2533'))
            p.drawRoundedRect(QRectF(7, 2, 54, 33), 17, 17)
        icon(self.glyph, '#EADDFF' if self.selected else '#A39AAE').paint(p, 23, 8, 22, 22)
        p.setPen(QColor('#EADDFF' if self.selected else '#A39AAE'))
        p.setFont(QFont('Segoe UI', 8))
        p.drawText(QRectF(0, 40, 68, 20), Qt.AlignmentFlag.AlignHCenter, self.title)


class HeroArt(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(230, 185)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for x, y, angle, front in [(65, 30, -15, False), (108, 17, 14, True)]:
            p.save()
            p.translate(x, y)
            p.rotate(angle)
            gradient = QLinearGradient(0, 0, 90, 130)
            gradient.setColorAt(0, QColor('#453252' if front else '#2C2635'))
            gradient.setColorAt(1, QColor('#24202C'))
            p.setBrush(gradient)
            p.setPen(QColor('#67567E' if front else '#49404F'))
            p.drawRoundedRect(QRectF(0, 0, 89, 129), 16, 16)
            if front:
                icon('play').paint(p, 31, 49, 28, 28)
            p.restore()
        p.setPen(QColor('#D0BCFF'))
        p.setFont(QFont('Segoe UI Symbol', 24))
        p.drawText(190, 42, '✦')
        p.setFont(QFont('Segoe UI Symbol', 17))
        p.drawText(20, 158, '✧')
        p.setPen(QPen(QColor('#6F5D87'), 2))
        p.drawLine(194, 148, 215, 136)


class FolderCard(QWidget):
    opened = Signal(str)
    menu_requested = Signal(str, object)

    def __init__(self, key, title, path, count=0, saved=False, available=True, parent=None):
        super().__init__(parent)
        self.key, self.title, self.path = key, title, path
        self.count, self.saved, self.available = count, saved, available
        self.cover = QPixmap()
        self.list_mode = False
        self.setMinimumWidth(230)
        self.setFixedHeight(230)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(f'{title}, {count} videos' if not saved else title)
        self.setToolTip(path if available else f'{path}\nFolder unavailable')

    def set_cover(self, path):
        reader = QImageReader(path)
        reader.setScaledSize(QSize(480, 270))
        self.cover = QPixmap.fromImage(reader.read())
        self.update()

    def set_list_mode(self, enabled):
        self.list_mode = enabled
        self.setFixedHeight(92 if enabled else 230)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        clip = QPainterPath()
        clip.addRoundedRect(r, 15, 15)
        p.setClipPath(clip)
        p.fillRect(r, QColor('#2B2631' if self.underMouse() else '#25232B'))
        image_rect = QRectF(0, 0, 150 if self.list_mode else self.width(), 92 if self.list_mode else 154)
        if not self.cover.isNull():
            source = QRectF(self.cover.rect())
            ratio = image_rect.width() / image_rect.height()
            if source.width() / source.height() > ratio:
                width = source.height() * ratio
                source.setLeft((source.width() - width) / 2)
                source.setWidth(width)
            else:
                height = source.width() / ratio
                source.setTop((source.height() - height) / 2)
                source.setHeight(height)
            p.drawPixmap(image_rect, self.cover, source)
        else:
            gradient = QLinearGradient(image_rect.topLeft(), image_rect.bottomRight())
            gradient.setColorAt(0, QColor('#4C395D'))
            gradient.setColorAt(1, QColor('#1C3035'))
            p.fillRect(image_rect, gradient)
            icon('folder', '#BAA2D2', 44).paint(p, int(image_rect.center().x()-22), int(image_rect.center().y()-22), 44, 44)
            p.setBrush(QColor('#10D0BCFF'))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(image_rect.topRight().toPoint(), 95, 95)
        shade = QLinearGradient(0, image_rect.height()/2, 0, image_rect.height())
        shade.setColorAt(0, QColor('#00000000'))
        shade.setColorAt(1, QColor('#850B0810'))
        p.fillRect(image_rect, shade)
        badge = 'Unavailable' if not self.available else ('Saved video' if self.saved else f'{self.count:,} videos')
        p.setFont(QFont('Segoe UI', 8))
        badge_width = p.fontMetrics().horizontalAdvance(badge) + 31
        p.setPen(QColor('#35FFFFFF'))
        p.setBrush(QColor('#B319161D'))
        badge_rect = QRectF(12, image_rect.height() - 35, badge_width, 23)
        p.drawRoundedRect(badge_rect, 6, 6)
        icon('play', '#E9E0F1', 11).paint(p, 20, int(image_rect.height())-29, 11, 11)
        p.setPen(QColor('#E9E0F1'))
        p.drawText(QRectF(35, badge_rect.y(), badge_width-23, 23), Qt.AlignmentFlag.AlignVCenter, badge)
        x, y = (168, 23) if self.list_mode else (17, 169)
        icon('bookmark' if self.saved else 'folder', '#D0BCFF', 18).paint(p, x, y+1, 18, 18)
        text_width = self.width()-x-62
        p.setFont(QFont('Segoe UI', 10, QFont.Weight.DemiBold))
        p.setPen(QColor('#F0E9F6'))
        p.drawText(QRectF(x+27, y-1, text_width, 23), Qt.AlignmentFlag.AlignVCenter,
                   p.fontMetrics().elidedText(self.title, Qt.TextElideMode.ElideRight, int(text_width)))
        p.setFont(QFont('Segoe UI', 8))
        p.setPen(QColor('#978CA4'))
        p.drawText(QRectF(x+27, y+26, text_width, 18), Qt.AlignmentFlag.AlignVCenter,
                   p.fontMetrics().elidedText(self.path, Qt.TextElideMode.ElideMiddle, int(text_width)))
        if not self.saved:
            dx, dy = (self.width()-35, 34) if self.list_mode else (self.width()-35, 12)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor('#B01C1723'))
            p.drawEllipse(QRectF(dx, dy, 25, 25))
            icon('more', '#DED3E8', 17).paint(p, dx+4, dy+4, 17, 17)
        p.setClipping(False)
        p.setPen(QPen(QColor('#A185BC' if self.underMouse() or self.hasFocus() else '#38323F'), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, 15, 15)

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.menu_requested.emit(self.key, event.globalPosition().toPoint())
        elif event.button() == Qt.MouseButton.LeftButton:
            if not self.saved and event.position().x() > self.width()-45 and ((self.list_mode and 20 < event.position().y() < 65) or (not self.list_mode and event.position().y() < 45)):
                self.menu_requested.emit(self.key, event.globalPosition().toPoint())
            else:
                self.opened.emit(self.key)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.opened.emit(self.key)
        else:
            super().keyPressEvent(event)


class AddCard(QPushButton):
    def __init__(self, callback, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(230)
        self.setFixedHeight(230)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(callback)
        self.setAccessibleName('Add a new video folder')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor('#292130' if self.underMouse() else '#1D1923'))
        pen = QPen(QColor('#655072' if self.underMouse() else '#49404F'), 1)
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawRoundedRect(QRectF(1, 1, self.width()-2, self.height()-2), 15, 15)
        c = self.rect().center()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#352C41'))
        p.drawRoundedRect(QRectF(c.x()-21, c.y()-53, 42, 42), 13, 13)
        icon('plus').paint(p, c.x()-11, c.y()-43, 22, 22)
        p.setFont(QFont('Segoe UI', 10))
        p.setPen(QColor('#CCB9E3'))
        p.drawText(QRectF(0, c.y()+3, self.width(), 22), Qt.AlignmentFlag.AlignCenter, 'A new folder. A new flow.')
        p.setFont(QFont('Segoe UI', 8))
        p.setPen(QColor('#93849F'))
        p.drawText(QRectF(0, c.y()+29, self.width(), 20), Qt.AlignmentFlag.AlignCenter, 'Bring your own videos.')


class VolumeButton(QPushButton):
    adjusted = Signal(int)

    def paintEvent(self, event):
        paint_action(self, 'mute' if self.text() == 'Muted' else 'sound', self.text())

    def wheelEvent(self, event):
        self.adjusted.emit(5 if event.angleDelta().y() > 0 else -5)
        event.accept()


class SeekSlider(QSlider):
    def apply_position(self, event):
        fraction = max(0, min(1, event.position().x()/max(1, self.width())))
        self.setValue(round(self.minimum() + fraction*(self.maximum()-self.minimum())))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(True)
            self.apply_position(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isSliderDown():
            self.apply_position(event)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.apply_position(event)
            self.setSliderDown(False)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


def paint_action(widget, glyph, text):
    p = QPainter(widget)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor('#6C5189' if widget.property('active') else '#382E41'))
    p.setBrush(QColor('#4F378B' if widget.property('active') else ('#3A2D47' if widget.underMouse() else '#2B2533')))
    p.drawRoundedRect(QRectF(1, 1, widget.width()-2, widget.height()-2), 17, 17)
    icon(glyph, '#EADDFF', 21).paint(p, (widget.width()-21)//2, 10, 21, 21)
    p.setFont(QFont('Segoe UI', 7))
    p.setPen(QColor('#E2D4EE'))
    p.drawText(QRectF(0, 35, widget.width(), 18), Qt.AlignmentFlag.AlignCenter, text)


class ActionButton(QPushButton):
    def __init__(self, text, glyph, callback, tooltip):
        super().__init__(text)
        self.glyph = glyph
        self.setFixedSize(62, 61)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.clicked.connect(callback)

    def paintEvent(self, event):
        paint_action(self, self.glyph, self.text())


class Toast(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName('toast')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 13, 20, 13)
        self.text = label('', 10, '#32223F')
        self.text.setWordWrap(True)
        layout.addWidget(self.text)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, text, duration=3800):
        self.text.setText(text)
        self.setFixedWidth(min(650, self.parentWidget().width()-120))
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        self.timer.start(duration)

    def reposition(self):
        self.move((self.parentWidget().width()-self.width())//2 + 30, self.parentWidget().height()-self.height()-28)
