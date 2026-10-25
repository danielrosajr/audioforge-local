"""Testes que não dependem de internet nem de modelos pesados."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audioforge import core


class TestCore(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(core.slug("Música: Olá / 2026"), "Musica-Ola-2026")

    def test_source_validation(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / "teste.wav"
            file.write_bytes(b"RIFF")
            self.assertEqual(core.validate_source("", str(file))[0], "arquivo")
            self.assertEqual(core.validate_source("https://youtu.be/abc", None)[0], "url")
            with self.assertRaises(core.AudioForgeError):
                core.validate_source("https://example.com/video", None)
            with self.assertRaises(core.AudioForgeError):
                core.validate_source("https://youtu.be/abc", str(file))
            with self.assertRaises(core.AudioForgeError):
                core.validate_source("", None)

    def test_srt_time(self):
        self.assertEqual(core.srt_time(62.054), "00:01:02,054")
        self.assertEqual(core.srt_time(3600.001), "01:00:00,001")
        self.assertEqual(core.srt_time(-1.0), "00:00:00,000")

    def test_wav_only_process_and_history(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "results"
            sample = Path(td) / "teste.wav"
            sample.write_bytes(b"RIFFTESTWAVE")
            with patch.object(core, "DATA_DIR", data_dir), patch.object(core, "HISTORY_FILE", data_dir / "historico.json"):
                record = core.process("", str(sample), False, False, "base", "auto", lambda _: None)
                self.assertTrue((Path(record["folder"]) / "original.wav").is_file())
                self.assertEqual(record["instrumental"], None)
                self.assertEqual(record["transcript"], "")
                self.assertEqual(len(core.read_history()), 1)
                self.assertEqual(len(core.history_choices()), 1)
                loaded = core.load_history_item(core.read_history()[0]["id"])
                self.assertEqual(loaded["files"], record["files"])


    def test_mock_transcription_files(self):
        from types import ModuleType, SimpleNamespace
        fake_module = ModuleType("faster_whisper")

        class FakeWhisper:
            def __init__(self, *args, **kwargs):
                self.settings = (args, kwargs)

            def transcribe(self, *_args, **_kwargs):
                return iter([
                    SimpleNamespace(start=0, end=1.25, text=" Olá mundo"),
                    SimpleNamespace(start=1.25, end=3, text=" Uma legenda"),
                ]), SimpleNamespace(language="pt")

        fake_module.WhisperModel = FakeWhisper
        with tempfile.TemporaryDirectory() as td, patch.dict("sys.modules", {"faster_whisper": fake_module}):
            folder = Path(td)
            transcription, files = core.transcribe_audio(folder / "dummy.wav", folder, "base", "pt", lambda _: None)
            self.assertIn("Olá mundo", transcription)
            self.assertEqual(len(files), 2)
            self.assertIn("00:00:01,250", files[1].read_text(encoding="utf-8"))
            self.assertTrue(files[0].is_file())

    def test_mock_demucs_output(self):
        from types import ModuleType
        fake_demucs = ModuleType("demucs")
        with tempfile.TemporaryDirectory() as td, patch.dict("sys.modules", {"demucs": fake_demucs}):
            folder = Path(td)
            input_file = folder / "original.wav"
            input_file.write_bytes(b"WAVE")

            def command(cmd, cb):
                out = Path(cmd[cmd.index("-o") + 1]) / "htdemucs" / "original"
                out.mkdir(parents=True, exist_ok=True)
                (out / "vocals.wav").write_bytes(b"VOCAL")
                (out / "no_vocals.wav").write_bytes(b"INST")

            def to_mp3(src, dst, cb):
                dst.write_bytes(b"mp3")

            with patch.object(core, "run_command", side_effect=command), patch.object(core, "wav_to_mp3", side_effect=to_mp3):
                inst, vocal, files = core.separate_audio(input_file, folder, lambda _: None)
                self.assertEqual(inst.name, "instrumental.mp3")
                self.assertEqual(vocal.name, "voz.mp3")
                self.assertEqual(len(files), 4)
                self.assertTrue(all(p.is_file() for p in files))

    def test_reject_unknown_history_id(self):
        with self.assertRaises(core.AudioForgeError):
            core.load_history_item("../../secret")


if __name__ == "__main__":
    unittest.main()
