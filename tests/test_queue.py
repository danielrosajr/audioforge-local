"""Fila e cancelamento, sem tocar no YouTube ou baixar modelos."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from audioforge import core
from audioforge.queue_manager import ProcessingQueue


def until(predicate, seconds=4):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.025)
    return False


class TestQueue(unittest.TestCase):
    def test_fifo_and_results(self):
        order=[]
        def fake(url,local,separate,transcribe,model,lang,status,exports,**kwargs):
            order.append(url)
            status('Baixando mídia: 50%')
            time.sleep(.12)
            return {'title':url,'files':[], 'folder':'/tmp'}
        with tempfile.TemporaryDirectory() as temp:
            queue=ProcessingQueue(Path(temp)/'uploads',fake)
            urls=[f'https://youtu.be/{i}' for i in range(3)]
            ids=[queue.enqueue(url,None,['mp3'],False,False,'base','auto') for url in urls]
            self.assertTrue(until(lambda: all(j['state']=='concluído' for j in queue.snapshot())))
            self.assertEqual(order, urls)
            self.assertEqual(queue.get_result(ids[1])['title'],urls[1])
            self.assertEqual(queue.snapshot()[0]['progress'],100)
            self.assertEqual(queue.clear_finished(),3)
            self.assertEqual(queue.snapshot(),[])
            self.assertTrue(queue.stop_if_idle())

    def test_cancel_waiting_job_does_not_run(self):
        gate=threading.Event()
        running=threading.Event()
        calls=[]
        def fake(url,*args,**kwargs):
            calls.append(url);running.set()
            gate.wait(timeout=2)
            return {'title':url,'files':[]}
        with tempfile.TemporaryDirectory() as temp:
            q=ProcessingQueue(Path(temp)/'cache',fake)
            first=q.enqueue('https://youtu.be/one',None,['wav'],False,False,'base','auto')
            self.assertTrue(running.wait(2))
            second=q.enqueue('https://youtu.be/two',None,['wav'],False,False,'base','auto')
            self.assertIn('antes de iniciar',q.cancel_job(second))
            gate.set()
            self.assertTrue(until(lambda:q.busy_count()==0))
            self.assertEqual(calls,['https://youtu.be/one'])
            self.assertIn('cancelado',[item['state'] for item in q.snapshot()])
            q.stop_if_idle()

    def test_cancel_running_job_cleans_upload(self):
        gate=threading.Event()
        def fake(url,local,*args,**kwargs):
            assert Path(local).is_file()
            while not kwargs['cancel_event'].is_set():
                time.sleep(.015)
            raise core.ProcessingCancelled('Solicitado')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source=root/'teste.wav';source.write_bytes(b'abcd')
            q=ProcessingQueue(root/'cache',fake)
            id_=q.enqueue('',str(source),['wav'],False,False,'tiny','auto')
            self.assertTrue(until(lambda:q.snapshot()[0]['state']=='processando'))
            result=q.cancel_job(id_)
            self.assertIn('Solicitação',result)
            self.assertTrue(until(lambda:q.snapshot()[0]['state']=='cancelado'))
            self.assertFalse((root/'cache'/id_).exists())
            self.assertTrue(source.exists())
            q.stop_if_idle()

    def test_validation_and_shutdown_when_busy(self):
        gate=threading.Event()
        started=threading.Event()
        def fake(*args,**kwargs):
            started.set();gate.wait(2)
            return {'title':'ok','files':[]}
        with tempfile.TemporaryDirectory() as temp:
            q=ProcessingQueue(Path(temp)/'s',fake)
            with self.assertRaisesRegex(core.AudioForgeError,'qualidade|Qualidade'):
                q.enqueue('https://youtu.be/x',None,['mp3'],False,False,'tiny','auto',999)
            q.enqueue('https://youtu.be/x',None,['mp3'],False,False,'tiny','auto',320,720)
            self.assertTrue(started.wait(2))
            self.assertFalse(q.stop_if_idle())
            gate.set()
            self.assertTrue(until(lambda:q.busy_count()==0))
            self.assertTrue(q.stop_if_idle())

    def test_html_escape_in_queue(self):
        import app
        with patch.object(app.TASKS,'snapshot', return_value=[dict(id='abc12345',title='<script>bad</script>',state='erro',message='<img src=x>',progress=None,files=0)]):
            html,dropdown,summary=app.queue_display()
            self.assertNotIn('<script>',html)
            self.assertNotIn('<img src=x>',html)
            self.assertIn('&lt;script&gt;',html)

    def test_mp3_quality_respects_selected_bitrate(self):
        import shutil
        import subprocess
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
            self.skipTest('FFmpeg indisponível')
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'input.wav'
            subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-y','-f','lavfi',
                            '-i','sine=frequency=700:duration=1','-ac','2',str(src)],check=True)
            core._job_context.mp3_bitrate=128
            try: core.media_to_mp3(src,Path(d)/'output.mp3',lambda _:None)
            finally: core._job_context.mp3_bitrate=192
            result=subprocess.run(['ffprobe','-v','error','-show_entries','format=bit_rate',
                         '-of','default=noprint_wrappers=1:nokey=1',str(Path(d)/'output.mp3')],
                         capture_output=True,text=True,check=True)
            self.assertLess(abs(int(result.stdout.strip())-128000),12000)

    def test_ffmpeg_cancel_terminates_process(self):
        # Emula um subprocesso ativo com o Python, e confirma interrupção rápida.
        import sys
        ev=threading.Event()
        errors=[]
        def do_work():
            core._job_context.cancel_event=ev
            try:
                core.run_command([sys.executable,'-c','import time; time.sleep(30)'],lambda _:None)
            except BaseException as exc:
                errors.append(exc)
            finally:
                core._job_context.cancel_event=None
        worker=threading.Thread(target=do_work)
        worker.start()
        time.sleep(.18)
        ev.set()
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertTrue(errors and isinstance(errors[0],core.ProcessingCancelled),errors)


if __name__=='__main__':unittest.main()
