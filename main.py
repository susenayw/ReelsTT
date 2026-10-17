from __future__ import annotations

# Must run before Qt, config loading, or any other application startup work.
# Velopack invokes this entry point for fast-exit install/update hooks.
if __name__ == '__main__':
    import velopack
    velopack.App().set_auto_apply_on_startup(False).run()

import argparse
import ctypes
import logging
from logging.handlers import RotatingFileHandler
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QMessageBox

from core.config import APP_DIR, DATA_DIR, RESOURCE_DIR, Config
from ui.theme import STYLE
from core.version import __version__


def main():
    parser = argparse.ArgumentParser(description='ReelsTT native local video feed')
    parser.add_argument('--folder', help='Add a folder to the library')
    parser.add_argument('--diagnostics', action='store_true', help='Write local RAM/playback diagnostics to data/runtime.json')
    args = parser.parse_args()
    handler = RotatingFileHandler(DATA_DIR / 'reelstt.log', maxBytes=2_000_000, backupCount=2, encoding='utf-8')
    logging.basicConfig(level=logging.INFO, handlers=[handler], format='%(asctime)s %(levelname)s %(message)s')
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ReelsTT.ReelFlow.1')
    app = QApplication(sys.argv[:1])
    app.setApplicationName('ReelsTT')
    app.setApplicationVersion(__version__)
    app.setOrganizationName('ReelsTT')
    app.setStyle('Fusion')
    app.setFont(QFont('Segoe UI', 10))
    app.setStyleSheet(STYLE)
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    import hashlib
    server_name = 'ReelsTT-' + hashlib.sha256(str(DATA_DIR).encode()).hexdigest()[:16]
    probe = QLocalSocket()
    probe.connectToServer(server_name)
    if probe.waitForConnected(300):
        probe.write((args.folder or 'activate').encode())
        probe.waitForBytesWritten(500)
        probe.disconnectFromServer()
        return 0
    QLocalServer.removeServer(server_name)
    server = QLocalServer(app)
    server.listen(server_name)
    if not (RESOURCE_DIR / 'native' / 'libmpv-2.dll').exists():
        QMessageBox.critical(None, 'MPV library missing', 'ReelsTT needs native/libmpv-2.dll beside its runtime. See README.md for setup.')
        return 1
    from ui.window import MainWindow
    config = Config()
    window = MainWindow(config, initial_folder=args.folder, diagnostics=args.diagnostics)

    def on_connection():
        connection = server.nextPendingConnection()
        if connection is None:
            return
        connection.waitForReadyRead(500)
        message = bytes(connection.readAll()).decode(errors='replace')
        if message and message != 'activate' and os.path.isdir(message):
            window.add_path(message)
        if window.isMinimized():
            window.showNormal()
        window.raise_()
        window.activateWindow()
        connection.disconnectFromServer()
        connection.deleteLater()

    server.newConnection.connect(on_connection)

    def exception_hook(kind, value, trace):
        logging.error('Unhandled application exception', exc_info=(kind, value, trace))
        if window.isVisible():
            window.toast(f'Something went wrong: {value}. Details are in data/reelstt.log.', 8000)

    sys.excepthook = exception_hook
    window.show()
    logging.info('Started ReelsTT pid=%s', os.getpid())
    result = app.exec()
    server.close()
    return result


if __name__ == '__main__':
    raise SystemExit(main())
