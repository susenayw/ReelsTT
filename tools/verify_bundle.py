"""Confirm the frozen Python modules exactly match current source bytecode."""
from pathlib import Path
import types
from PyInstaller.archive.readers import ZlibArchiveReader

root = Path(__file__).resolve().parents[1]
archive = ZlibArchiveReader(str(root / 'build' / 'ReelsTT' / 'PYZ-00.pyz'))


def signature(code):
    if not isinstance(code, types.CodeType):
        return code
    return (code.co_code, code.co_names, code.co_varnames, code.co_flags,
            tuple(signature(c) for c in code.co_consts))


for module in ('core.config', 'core.library', 'core.player', 'core.thumbnails',
               'ui.theme', 'ui.widgets', 'ui.window'):
    source = root / (module.replace('.', '/')+'.py')
    current = compile(source.read_bytes(), str(source), 'exec', dont_inherit=True)
    assert signature(current) == signature(archive.extract(module)), f'Stale packaged module: {module}'
    print('MATCH', module)
