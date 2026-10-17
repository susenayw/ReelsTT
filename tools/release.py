"""Build Windows x64 Velopack release artifacts without publishing them."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.version import __version__
VPK_VERSION = '1.2.161'
VPK_SHA256 = '2b56ce117f803fc70c103cb423bd040e395e40370f6ff6e10818e9ff9c26a323'
def run(*args):
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True)

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

if sys.platform != 'win32':
    raise SystemExit('Build on Windows x64')
run(sys.executable, ROOT / 'tools/bootstrap_native.py')
cache = ROOT / '.release-tools'
cache.mkdir(exist_ok=True)
archive = cache / 'vpk.nupkg'
if not archive.exists():
    urllib.request.urlretrieve(f'https://github.com/velopack/velopack/releases/download/{VPK_VERSION}/vpk.{VPK_VERSION}.nupkg', archive)
if sha(archive) != VPK_SHA256:
    raise RuntimeError('Velopack CLI checksum mismatch')
cli = cache / 'vpk/tools/net8.0/any/vpk.dll'
if not cli.exists():
    with zipfile.ZipFile(archive) as z:
        z.extractall(cache / 'vpk')
run(sys.executable, ROOT / 'tools/build.py')
run(sys.executable, ROOT / 'tools/verify_bundle.py')
# Create a branded progress splash using the same application icon.
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QRectF
app = QApplication.instance() or QApplication([])
splash = QPixmap(520, 260)
splash.fill(QColor('#11121a'))
painter = QPainter(splash)
QSvgRenderer(str(ROOT / 'assets/reelstt.svg')).render(painter, QRectF(38, 48, 86, 86))
painter.setPen(QColor('#f3f0ff'))
painter.setFont(QFont('Segoe UI', 28, QFont.Weight.Bold))
painter.drawText(148, 97, 'ReelsTT')
painter.setFont(QFont('Segoe UI', 12))
painter.setPen(QColor('#b9b5ca'))
painter.drawText(150, 129, f'{__version__} / Preview')
painter.drawText(40, 205, 'Your videos. Your flow.')
painter.end()
assert splash.save(str(cache / 'splash.png'))
run('dotnet', cli, 'pack', '--packId', 'SUWS.ReelsTT',
    '--packVersion', __version__, '--packDir', ROOT / 'build-output/ReelsTT',
    '--mainExe', 'ReelsTT.exe', '--packTitle', 'ReelsTT', '--packAuthors', 'SUWS',
    '--runtime', 'win-x64', '--channel', 'win-preview',
    '--icon', ROOT / 'assets/reelstt.ico', '--splashImage', cache / 'splash.png',
    '--splashProgressColor', '#B6A0F5', '--shortcuts', 'StartMenuRoot',
    '--releaseNotes', ROOT / 'RELEASE_NOTES.md', '--outputDir', ROOT / 'Releases')
# Include the source/license index independently of installation.
releases = ROOT / 'Releases'
with zipfile.ZipFile(releases / f'ReelsTT-{__version__}-licenses.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for file in [ROOT / 'LICENSE', ROOT / 'THIRD_PARTY.md', *sorted((ROOT / 'licenses').rglob('*'))]:
        if file.is_file():
            z.write(file, file.relative_to(ROOT))
files = [f for f in sorted(releases.iterdir()) if f.is_file() and f.name != 'SHA256SUMS.txt']
(releases / 'SHA256SUMS.txt').write_text(''.join(f'{sha(f)}  {f.name}\n' for f in files), encoding='utf-8')
print('Release ready:', releases)
