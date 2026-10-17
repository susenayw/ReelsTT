"""Installed data must survive replacement of Velopack version directories."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from core import config

class InstalledDataTests(unittest.TestCase):
    def test_new_installed_versions_share_stable_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.dict(os.environ, {'LOCALAPPDATA': str(root / 'local')}, clear=True), patch.object(config.sys, 'frozen', True, create=True):
                for version in ('app-0.0.100', 'app-0.0.101'):
                    with patch.object(config, 'APP_DIR', root / version):
                        self.assertEqual(config.default_data_directory(), root / 'local' / 'ReelsTT')

    def test_existing_portable_preferences_are_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'data').mkdir()
            (root / 'data/config.json').write_text('{}')
            with patch.object(config, 'APP_DIR', root), patch.object(config.sys, 'frozen', True, create=True), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(config.default_data_directory(), root / 'data')

    def test_explicit_override_takes_priority(self):
        with patch.dict(os.environ, {'REELSTT_DATA_DIR': 'custom-data'}):
            self.assertEqual(config.default_data_directory(), Path('custom-data'))
