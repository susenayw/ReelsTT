"""Install an already-built portable directory after ReelsTT has closed."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
output = root / 'build-output' / 'ReelsTT'
shutil.copy2(output / 'ReelsTT.exe', root / 'ReelsTT.exe')
shutil.copytree(output / '_runtime', root / '_runtime', dirs_exist_ok=True)
for runtime in (output / '_runtime', root / '_runtime'):
    for name in ('icuuc.dll', 'icudt78.dll'):
        (runtime / name).unlink(missing_ok=True)
print('Installed:', root / 'ReelsTT.exe')
