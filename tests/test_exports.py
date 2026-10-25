"""Testes dos novos formatos e compatibilidade com resultados anteriores."""

import json
import math
import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from audioforge import core


class TestExports(unittest.TestCase):
    def test_format_validation(self):
        self.assertEqual(core.normalize_exports(None), ["wav"])
        self.assertEqual(core.normalize_exports(["mp4", "wav", "mp3", "mp4"]), ["wav", "mp3", "mp4"])
        self.assertEqual(core.normalize_exports([]), [])
        for bad in (["exe"], "mp3", [42], ["wav", None]):
            with self.assertRaises(core.AudioForgeError):
                core.normalize_exports(bad)

    def test_only_mp3_from_link_avoids_intermediate_wav(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            results = root / "results"
            def downloader(_url, folder, status):
                path = folder / "original.mp3"
                path.write_bytes(b"FAKE MP3")
                return path, "Teste MP3"
            with patch.object(core, "DATA_DIR", results), patch.object(core, "HISTORY_FILE", results / "historico.json"), \
                 patch.object(core, "download_youtube_mp3", side_effect=downloader), \
                 patch.object(core, "download_youtube_audio", side_effect=AssertionError("Nao baixar WAV")), \
                 patch.object(core, "download_youtube_mp4", side_effect=AssertionError("Nao baixar MP4")):
                result = core.process("https://youtu.be/test", None, False, False, "base", "auto", lambda _: None, ["mp3"])
                self.assertEqual(Path(result["original_audio"]).suffix, ".mp3")
                self.assertEqual([Path(x).name for x in result["files"]], ["original.mp3"])
                self.assertFalse((Path(result["folder"]) / "original.wav").exists())
                self.assertIsNone(result["video"])
                self.assertEqual(core.read_history()[0]["operations"], "MP3")

    def test_only_mp4_from_link_avoids_intermediate_audio(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            results = root / "results"
            def downloader(_url, folder, status):
                path = folder / "original.mp4"
                path.write_bytes(b"FAKE VIDEO")
                return path, "Teste MP4"
            with patch.object(core, "DATA_DIR", results), patch.object(core, "HISTORY_FILE", results / "historico.json"), \
                 patch.object(core, "download_youtube_mp4", side_effect=downloader), \
                 patch.object(core, "convert_to_wav", side_effect=AssertionError("Nao extrair WAV")), \
                 patch.object(core, "media_to_mp3", side_effect=AssertionError("Nao extrair MP3")):
                result = core.process("https://youtu.be/test", None, False, False, "base", "auto", lambda _: None, ["mp4"])
                self.assertEqual(Path(result["video"]).name, "original.mp4")
                self.assertIsNone(result["original_audio"])
                self.assertEqual([Path(x).name for x in result["files"]], ["original.mp4"])

    def test_video_and_audio_export_together(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            results = root / "results"
            def get_video(_url, folder, status):
                path = folder / "original.mp4"
                path.write_bytes(b"VIDEO")
                return path, "Dois formatos"
            def converter(source, destination, status):
                destination.write_bytes(b"SAMPLE")
            with patch.object(core, "DATA_DIR", results), patch.object(core, "HISTORY_FILE", results / "historico.json"), \
                 patch.object(core, "download_youtube_mp4", side_effect=get_video), \
                 patch.object(core, "convert_to_wav", side_effect=converter), \
                 patch.object(core, "media_to_mp3", side_effect=converter):
                result = core.process("https://youtu.be/test", None, False, False, "base", "auto", lambda _: None, ["wav", "mp3", "mp4"])
                self.assertEqual({Path(p).name for p in result["files"]}, {"original.wav", "original.mp3", "original.mp4"})
                self.assertEqual(core.read_history()[0]["operations"], "WAV + MP3 + MP4")

    def test_cleanup_intermediate_wav_after_ai(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            results = root / "results"
            source = root / "song.wav"
            source.write_bytes(b"WAVE")
            def separate(_source, folder, _status):
                i = folder / "instrumental.mp3"
                v = folder / "voz.mp3"
                i.write_bytes(b"A")
                v.write_bytes(b"B")
                return i, v, [i, v]
            with patch.object(core, "DATA_DIR", results), patch.object(core, "HISTORY_FILE", results / "historico.json"), \
                 patch.object(core, "separate_audio", side_effect=separate):
                result = core.process("", str(source), True, False, "base", "auto", lambda _: None, [])
                self.assertFalse((Path(result["folder"]) / "original.wav").exists())
                self.assertEqual(len(result["files"]), 2)
                self.assertEqual(core.read_history()[0]["operations"], "Karaokê")

    def test_mp4_audio_only_rejected_before_creating_folder(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            file = root / "original.mp3"
            file.write_bytes(b"FAKE")
            results = root / "results"
            with patch.object(core, "DATA_DIR", results):
                with self.assertRaisesRegex(core.AudioForgeError, "exige uma entrada com vídeo"):
                    core.process("", str(file), False, False, "base", "auto", lambda _: None, ["mp4"])
                self.assertFalse(results.exists())

    def test_previous_history_is_readable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            item_id = "012345abcdef"
            folder = root / item_id
            folder.mkdir()
            (folder / "original.wav").write_bytes(b"RIFF")
            (folder / "transcricao.txt").write_text("olá", encoding="utf-8")
            history = [{"id": item_id, "title": "Antigo", "date": "24/10/2026", "files": ["original.wav", "transcricao.txt"], "operations": "WAV"}]
            (root / "historico.json").write_text(json.dumps(history), encoding="utf-8")
            with patch.object(core, "DATA_DIR", root), patch.object(core, "HISTORY_FILE", root / "historico.json"):
                saved = core.load_history_item(item_id)
                self.assertEqual(saved["transcript"], "olá")
                self.assertEqual(Path(saved["original_audio"]).name, "original.wav")
                self.assertIsNone(saved["video"])

    def test_ytdlp_format_settings_are_selected_correctly(self):
        from types import ModuleType
        import sys
        fake = ModuleType("yt_dlp")
        captured = []

        class FakeDownloader:
            def __init__(self, options):
                self.options = options
                captured.append(options)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return None
            def extract_info(self, url, download):
                assert download is True and url.startswith("https://")
                suffix = ".mp4" if self.options.get("merge_output_format") == "mp4" else ".mp3"
                Path(self.options["outtmpl"].replace("%(ext)s", suffix[1:])).write_bytes(b"MOCK")
                return {"title": "Vídeo de teste"}

        fake.YoutubeDL = FakeDownloader
        with tempfile.TemporaryDirectory() as td, patch.dict(sys.modules, {"yt_dlp": fake}):
            folder = Path(td)
            mp3, _ = core.download_youtube_mp3("https://youtu.be/test", folder, lambda _: None)
            mp4, _ = core.download_youtube_mp4("https://youtu.be/test", folder, lambda _: None)
            self.assertEqual(mp3.suffix, ".mp3")
            self.assertEqual(mp4.suffix, ".mp4")
            self.assertEqual(captured[0]["postprocessors"][0]["preferredcodec"], "mp3")
            self.assertIn("ba[ext=m4a]", captured[1]["format"])
            self.assertEqual(captured[1]["merge_output_format"], "mp4")
            self.assertTrue(all(options["noplaylist"] for options in captured))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg ausente")
    def test_real_ffmpeg_audio_and_video_export(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_wav = root / "sample.wav"
            with wave.open(str(input_wav), "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(2)
                writer.setframerate(16000)
                samples = bytearray()
                for i in range(4800):
                    v = int(1000 * math.sin(2 * math.pi * 440 * i / 16000))
                    samples.extend(v.to_bytes(2, "little", signed=True))
                writer.writeframes(samples)
            mp3 = root / "sample.mp3"
            core.media_to_mp3(input_wav, mp3, lambda _: None)
            self.assertGreater(mp3.stat().st_size, 500)
            video = root / "sample.mkv"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-f", "lavfi", "-i", "color=c=purple:s=96x64:r=10:d=0.5",
                "-i", str(input_wav), "-shortest", "-c:v", "mpeg4", "-c:a", "aac", str(video),
            ], check=True, timeout=25)
            output_mp4 = root / "converted.mp4"
            core.convert_to_mp4(video, output_mp4, lambda _: None)
            self.assertGreater(output_mp4.stat().st_size, 500)
            probe = subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries", "stream=codec_name", "-of", "json", str(output_mp4),
            ], text=True)
            self.assertIn("h264", probe)


if __name__ == "__main__":
    unittest.main()
