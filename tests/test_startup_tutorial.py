"""Self-contained checks for guided tour and per-user single-instance startup."""
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import app
from audioforge import tutorial
from audioforge import single_instance

ROOT = Path(__file__).resolve().parents[1]


class TestTour(unittest.TestCase):
    def test_steps_and_tab_focus(self):
        self.assertEqual(len(tutorial.STEPS), 7)
        self.assertEqual(app.tour_start()[0], 0)
        self.assertIn("PASSO 1 DE 7", app.tour_start()[1])
        self.assertIn("marker-source", app.tour_start()[2])
        self.assertEqual(app.tour_next(4)[0], 5)
        self.assertEqual(app.tour_next(5)[0], 6)
        self.assertEqual(app.tour_back(0)[0], 0)
        self.assertEqual(app.tour_back(5)[0], 4)

    def test_complete_and_skip_persist_across_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            config_dir = Path(folder) / 'config'
            with patch.object(tutorial, 'CONFIG_DIR', config_dir), \
                 patch.object(tutorial, 'SETTINGS_FILE', config_dir/'preferences.json'):
                self.assertFalse(tutorial.tutorial_was_seen())
                result = app.tour_next(6)
                self.assertEqual(result[2], '')
                self.assertTrue(tutorial.tutorial_was_seen())
                data = json.loads((config_dir/'preferences.json').read_text())
                self.assertTrue(data['tutorial_seen'])
                data['another_setting'] = 'preserved'
                (config_dir/'preferences.json').write_text(json.dumps(data))
                app.tour_skip()
                self.assertEqual(json.loads((config_dir/'preferences.json').read_text())['another_setting'], 'preserved')


class TestSingleInstance(unittest.TestCase):
    def test_busy_port_without_lock_does_not_reuse_unknown_service(self):
        with tempfile.TemporaryDirectory() as folder, \
             socket.socket() as s, \
             patch.object(single_instance, 'CACHE_DIR', Path(folder)), \
             patch.object(single_instance, 'LOCK_FILE', Path(folder)/'instance.lock'), \
             patch.object(single_instance, 'INFO_FILE', Path(folder)/'instance.json'), \
             patch.object(single_instance, 'app_port', lambda: s.getsockname()[1]):
            s.bind(('127.0.0.1', 0))
            s.listen(1)
            launched=[]
            self.assertEqual(single_instance.run_single_instance(lambda ready: launched.append('started')), 3)
            self.assertEqual(launched, [])
            self.assertFalse((Path(folder)/'instance.json').exists())

    def test_second_launch_reuses_first_and_exit_releases_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port=probe.getsockname()[1]
            env={**os.environ, 'XDG_CACHE_HOME':str(root/'cache'), 'AUDIOFORGE_PORT':str(port),
                 'BROWSER':'false', 'DISPLAY':'', 'WAYLAND_DISPLAY':''}
            code='from audioforge.single_instance import run_single_instance; raise SystemExit(run_single_instance(lambda ready: ready()))'
            first=subprocess.Popen([sys.executable,'-c',code], cwd=ROOT, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            info_file = root/'cache'/'audioforge-local'/'instance.json'
            try:
                for _ in range(90):
                    if info_file.exists() and single_instance._status(json.loads(info_file.read_text())):
                        break
                    if first.poll() is not None:
                        self.fail('First process exited before it was ready')
                    time.sleep(.1)
                self.assertTrue(info_file.exists())
                second=subprocess.run([sys.executable,'-c',code], cwd=ROOT, env=env,
                                       capture_output=True, text=True, timeout=10)
                self.assertEqual(second.returncode, 0, second.stderr)
                self.assertIn('Reutilizando', second.stdout)
                self.assertIsNone(first.poll())
            finally:
                if first.poll() is None:
                    first.send_signal(signal.SIGTERM)
                first.communicate(timeout=10)
            self.assertFalse(info_file.exists())


if __name__ == '__main__':
    unittest.main()
