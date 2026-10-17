"""Build a portable Windows app, retaining an editable source project."""
from pathlib import Path
import subprocess
import sys
import shutil
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtWidgets import QApplication
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt

app = QApplication([])
pixmap = QPixmap(256, 256)
pixmap.fill(Qt.GlobalColor.transparent)
painter = QPainter(pixmap)
QSvgRenderer(str(ROOT / 'assets' / 'reelstt.svg')).render(painter)
painter.end()
assert pixmap.save(str(ROOT / 'assets' / 'reelstt.ico'), 'ICO')

subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--windowed',
                '--onedir', '--name', 'ReelsTT', '--contents-directory', '_runtime',
                '--distpath', str(ROOT / 'build-output'), '--workpath', str(ROOT / 'build'),
                '--icon', str(ROOT / 'assets' / 'reelstt.ico'),
                '--add-binary', str(ROOT / 'native' / 'libmpv-2.dll')+';native',
                '--add-data', str(ROOT / 'assets')+';assets',
                '--collect-all', 'imageio_ffmpeg', '--collect-all', 'velopack',
                '--version-file', str(ROOT / 'tools' / 'windows-version.txt'),
                '--add-data', str(ROOT / 'LICENSE')+';.',
                '--add-data', str(ROOT / 'THIRD_PARTY.md')+';.',
                '--add-data', str(ROOT / 'licenses')+';licenses',
                '--hidden-import', 'PySide6.QtNetwork', '--hidden-import', 'PySide6.QtSvg',
                '--exclude-module', 'tkinter', '--exclude-module', 'PySide6.QtQml',
                '--exclude-module', 'PySide6.QtQuick', '--exclude-module', 'PySide6.QtOpenGL',
                str(ROOT / 'main.py')], cwd=ROOT, check=True)
output = ROOT / 'build-output' / 'ReelsTT'
# Qt uses Windows' ICU. Do not ship an unrelated DLL discovered on PATH.
for name in ('icuuc.dll', 'icudt78.dll'):
    (output / '_runtime' / name).unlink(missing_ok=True)
print('Built application:', output)
