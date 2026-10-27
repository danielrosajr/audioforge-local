"""Regression tests for new lyric editor, English UI, ASS and real export."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
from audioforge import karaoke, core, preferences


class KaraokeTests(unittest.TestCase):
    def test_distribute_and_validate(self):
        rows = karaoke.distribute_lines('Olá, mundo!\nHello world', 8)
        self.assertEqual(rows, [[0.0,4.0,'Olá, mundo!'],[4.0,8.0,'Hello world']])
        self.assertEqual(len(karaoke.validate_rows(rows)),2)
        with self.assertRaises(karaoke.KaraokeError):karaoke.validate_rows([[5,1,'invalid']])
        with self.assertRaises(karaoke.KaraokeError):karaoke.validate_rows([])
        with self.assertRaises(karaoke.KaraokeError):karaoke.distribute_lines('',5)

    def test_parse_srt_pt_and_en(self):
        txt='1\n00:00:00,100 --> 00:00:01,250\nBom dia\n\n2\n00:00:02,200 --> 00:00:03,000\nHello world\n'
        self.assertEqual(karaoke.parse_srt(txt),[[.1,1.25,'Bom dia'],[2.2,3.0,'Hello world']])

    def test_ass_progressive_and_escape(self):
        ass=karaoke.make_ass([[0.1,2,'Olá {\\bad} Hello!']],color='#A1C2E3')
        self.assertIn(r'{\kf',ass)
        self.assertIn('Olá',ass)
        self.assertNotIn('{\\bad}',ass)
        self.assertIn('&H00E3C2A1&',ass)
        static=karaoke.make_ass([[1,2,'Olá']],progressive=False)
        self.assertNotIn(r'\kf',static)
        with self.assertRaises(karaoke.KaraokeError):karaoke.make_ass([[0,1,'hi']],color='red')

    def test_timeline_html_xss(self):
        out=karaoke.timeline_html([[0,1,'<script>bad</script>']],language='en')
        self.assertNotIn('<script>',out)
        self.assertIn('&lt;script&gt;',out)
        self.assertIn('Timeline',out)

    def test_locale_updates_persist_without_erasing_tour(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(preferences,'SETTINGS_FILE',Path(tmp)/'prefs.json'),patch.object(preferences,'CONFIG_DIR',Path(tmp)):
            preferences.SETTINGS_FILE.write_text('{"tutorial_seen":true}',encoding='utf-8')
            preferences.save_language('en')
            self.assertEqual(preferences.get_language(),'en')
            saved=json.loads(preferences.SETTINGS_FILE.read_text())
            self.assertTrue(saved['tutorial_seen'])
            self.assertEqual(len(app.translate_controls('en')),78)
            self.assertEqual(preferences.get_language(),'en')

    def test_saved_project_reopens_and_renders_media(self):
        if not (shutil.which('ffmpeg') and shutil.which('ffprobe')):
            self.skipTest('FFmpeg unavailable')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            projects=root/'projects'
            movie=root/'video sample.mp4'
            audio=root/'music.wav'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','color=c=navy:s=320x180:r=15:d=1.5','-c:v','libx264','-pix_fmt','yuv420p',str(movie)],check=True)
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i','sine=frequency=440:duration=1.5','-c:a','pcm_s16le',str(audio)],check=True)
            with patch.object(karaoke,'PROJECTS_DIR',projects):
                id_,saved=karaoke.save_project(None,str(movie),str(audio),[[0,1.3,'Hello world!']],language='en')
                self.assertTrue(Path(saved).exists())
                item=karaoke.load_project(id_)
                self.assertEqual(item['language'],'en')
                # Input files are copied to a durable project directory.
                self.assertTrue(Path(item['video']).is_relative_to(projects))
                output,ass=karaoke.export_video(id_,[[0,1.3,'Hello world!']],'en')
                self.assertTrue(Path(output).is_file())
                self.assertTrue(Path(ass).is_file())
                probe=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_type','-of','json',output],capture_output=True,text=True,check=True)
                streams=[item['codec_type'] for item in json.loads(probe.stdout)['streams']]
                self.assertIn('video',streams)
                self.assertIn('audio',streams)
                self.assertGreater(Path(output).stat().st_size,1000)
                self.assertEqual(len(karaoke.project_choices()),1)
                with self.assertRaises(karaoke.KaraokeError):karaoke.load_project('../../secret')


if __name__=='__main__':unittest.main()
