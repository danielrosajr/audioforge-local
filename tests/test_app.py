"""Ações de interface que não devem matar o processo durante os testes."""
import unittest
from unittest.mock import patch

import app


class TestApp(unittest.TestCase):
    def tearDown(self):
        app.ACTIVE_JOBS = 0
        app.SHUTTING_DOWN = False

    def test_prevent_shutdown_with_active_job(self):
        app.ACTIVE_JOBS = 1
        with patch.object(app.threading, "Timer") as timer:
            msg = app.shutdown_app()
            self.assertIn("processamento(s) em execução", msg)
            self.assertFalse(app.SHUTTING_DOWN)
            timer.assert_not_called()

    def test_request_shutdown_once_with_confirmation_callback(self):
        app.ACTIVE_JOBS = 0
        with patch.object(app.threading, "Timer") as timer:
            msg = app.shutdown_app()
            self.assertIn("está encerrando", msg)
            timer.assert_called_once()
            self.assertTrue(app.SHUTTING_DOWN)
            msg2 = app.shutdown_app()
            self.assertIn("já foi solicitado", msg2)
            timer.assert_called_once()

    def test_build_gradio_interface(self):
        ui = app.build_interface()
        try:
            self.assertGreater(len(ui.blocks), 50)
        finally:
            ui.close()


if __name__ == "__main__":
    unittest.main()
