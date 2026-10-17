from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from core.config import Config
from core.library import scan_folder
from core.player import PlayerPool


class ConfigurationTests(unittest.TestCase):
    def test_folder_deduplication_and_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            c = Config(Path(directory))
            self.assertTrue(c.add_folder(directory))
            self.assertFalse(c.add_folder(directory))
            self.assertTrue(c.toggle_favorite('D:/Example/a.mp4'))
            self.assertIn('D:/Example/a.mp4', Config(Path(directory)).get('favorites'))
            self.assertFalse(c.toggle_favorite('D:/Example/a.mp4'))
            self.assertEqual(Config(Path(directory)).get('favorites'), [])

    def test_corrupt_settings_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'config.json').write_text('{broken', encoding='utf-8')
            c = Config(path)
            self.assertEqual(c.get('folders'), [])
            self.assertTrue((path / 'config.broken.json').exists())

    def test_invalid_types_and_volume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'config.json').write_text(json.dumps({'folders': ['D:/a', 5], 'favorites': 'invalid', 'volume': 999}), encoding='utf-8')
            c = Config(path)
            self.assertEqual(c.get('folders'), ['D:/a'])
            self.assertEqual(c.get('favorites'), [])
            self.assertEqual(c.get('volume'), 100)


class ScannerTests(unittest.TestCase):
    def test_recursive_mixed_formats_and_nonvideo_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'nested').mkdir()
            for name in ['a.MP4', 'b.mkv', 'readme.txt', 'nested/c.webm', 'nested/d.mov']:
                (path / name).write_bytes(b'')
            self.assertEqual(len(scan_folder(directory).videos), 4)
            self.assertEqual(len(scan_folder(directory, recursive=False).videos), 2)

    def test_missing_folder_has_explicit_state(self):
        result = scan_folder('Z:/reelstt-missing-test-drive/folder')
        self.assertFalse(result.available)
        self.assertEqual(result.videos, [])

    def test_cancel_large_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'a.mp4').touch()
            result = scan_folder(directory, cancelled=lambda: True)
            self.assertEqual(result.videos, [])


class MemoryPolicyTests(unittest.TestCase):
    def test_pressure_releases_only_background_players(self):
        current, previous, following = object(), object(), object()
        pool = Mock()
        pool.current = current
        pool.slots = [previous, current, following]
        pool._conserve = False
        pool._warning_sent = False
        with patch('core.player.memory_usage_mb', return_value=420):
            PlayerPool.check_memory(pool)
        self.assertTrue(pool._conserve)
        self.assertEqual(pool.destroy_slot.call_count, 2)
        pool.destroy_slot.assert_any_call(previous)
        pool.destroy_slot.assert_any_call(following)
        pool.preloader.stop.assert_called_once()

    def test_no_preload_in_memory_saver(self):
        pool = Mock()
        pool._conserve = True
        pool.current = object()
        PlayerPool.preload(pool)
        pool.create_slot.assert_not_called()

    def test_private_commit_pressure_also_releases_neighbors(self):
        current, neighbor = object(), object()
        pool = Mock()
        pool.current, pool.slots = current, [current, neighbor]
        pool._conserve, pool._warning_sent = False, False
        with patch('core.player.memory_usage_mb', return_value=320), \
             patch('core.player.committed_memory_mb', return_value=450):
            PlayerPool.check_memory(pool)
        self.assertTrue(pool._conserve)
        pool.destroy_slot.assert_called_once_with(neighbor)

    def test_preload_leaves_commit_headroom(self):
        pool = Mock()
        pool.current, pool._conserve = object(), False
        pool.index, pool.paths = 0, ['a.mp4', 'b.mp4']
        with patch('core.player.memory_usage_mb', return_value=300), \
             patch('core.player.committed_memory_mb', return_value=380):
            PlayerPool.preload(pool)
        pool.create_slot.assert_not_called()


class DeletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_recycle_failure_restores_original_playlist(self):
        from PySide6.QtWidgets import QMessageBox
        from ui.window import MainWindow
        window = Mock()
        window.current_path = 'D:/Example/keep-me.mp4'
        window.pool.paths = [window.current_path, 'D:/Example/next.mp4']
        window.pool.index = 0
        window.pool.current.player.pause = False
        paths = window.pool.paths[:]
        with patch('ui.window.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes), \
             patch('send2trash.send2trash', side_effect=OSError('File locked')) as trash:
            MainWindow.delete_video(window)
        trash.assert_called_once_with('D:/Example/keep-me.mp4')
        window.pool.release_path.assert_called_once()
        window.pool.set_playlist.assert_called_once_with(paths, 0)
        window.show_library.assert_not_called()

    def test_cancel_keeps_file_and_playback_state(self):
        from PySide6.QtWidgets import QMessageBox
        from ui.window import MainWindow
        window = Mock()
        window.current_path = 'D:/Example/keep-me.mp4'
        window.pool.current.player.pause = False
        with patch('ui.window.QMessageBox.question', return_value=QMessageBox.StandardButton.Cancel), \
             patch('send2trash.send2trash') as trash:
            MainWindow.delete_video(window)
        trash.assert_not_called()
        window.pool.release_path.assert_not_called()
        self.assertFalse(window.pool.current.player.pause)


if __name__ == '__main__':
    unittest.main()
