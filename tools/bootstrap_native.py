"""Fetch and verify the exact Windows x64 playback library."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
info = json.loads((ROOT / 'native/provenance.json').read_text())
def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
target = ROOT / 'native/libmpv-2.dll'
if target.exists() and digest(target) == info['dll_sha256']:
    print('Verified existing libmpv')
else:
    with tempfile.TemporaryDirectory(prefix='reelstt-native-') as temp:
        folder = Path(temp)
        archive = folder / 'mpv.7z'
        urllib.request.urlretrieve(info['download_url'], archive)
        if digest(archive) != info['archive_sha256']:
            raise RuntimeError('Native download checksum mismatch')
        subprocess.run(['tar', '-xf', str(archive), '-C', str(folder)], check=True)
        matches = list(folder.rglob('libmpv-2.dll'))
        if len(matches) != 1 or digest(matches[0]) != info['dll_sha256']:
            raise RuntimeError('Native library checksum mismatch')
        shutil.copy2(matches[0], target)
    print('Downloaded and verified libmpv')
