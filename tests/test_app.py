"""Pruebas de interacción Streamlit con Ollama simulado, sin GPU."""
import unittest
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest
from test_core import FakeClient, FakeEncoder, verdict
from nikali.config import ROOT
from nikali.rag import Retriever, load_chunks
from nikali.index import PreparedCorpus


class AppTests(unittest.TestCase):
    def setUp(self):
        st.cache_resource.clear()
        self.client = FakeClient()
        self.patcher = patch('nikali.config.make_client', return_value=self.client)
        self.patcher.start()
        self.encoder = FakeEncoder()
        prepared = PreparedCorpus(load_chunks(), ((1.0, 0.0), (0.0, 1.0)), "test", {})
        self.prepared_patcher = patch("nikali.index.load_prepared", return_value=prepared)
        self.prepared_patcher.start()
        self.addCleanup(self.prepared_patcher.stop)
        self.open_patcher = patch("nikali.index.open_retriever", side_effect=lambda data, **kw: Retriever(data.chunks, data.vectors, encoder=self.encoder))
        self.open_patcher.start()
        self.addCleanup(self.open_patcher.stop)
        self.embed_patcher = patch("nikali.rag.make_embedder", return_value=self.encoder)
        self.embed_patcher.start()
        self.addCleanup(self.embed_patcher.stop)
        self.addCleanup(self.patcher.stop)
        self.addCleanup(st.cache_resource.clear)
        self.app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=15)

    def test_switch_modes_and_reset_are_isolated(self):
        app = self.app.run()
        self.assertFalse(app.exception)
        self.client.replies = [verdict('CORRECTO')]
        app.chat_input[0].set_value('f(u)=sin(u), g(x)=x²').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['guided']['step'], 1)
        app.radio[0].set_value('Explorar conceptos').run()
        self.assertEqual(len(app.chat_message), 0)
        self.client.replies = ['Se multiplican las razones de cambio.']
        app.chat_input[0].set_value('¿Qué es la regla de la cadena?').run()
        self.assertEqual(len(app.session_state['free']['messages']), 2)
        app.radio[0].set_value('Ejercicio guiado').run()
        self.assertEqual(app.session_state['guided']['step'], 1)
        app.button(key='reset').click().run()
        self.assertEqual(app.session_state['guided']['step'], 0)
        self.assertEqual(len(app.session_state['free']['messages']), 2)
        self.assertFalse(app.exception)

    def test_failed_turn_can_retry_without_duplicate_messages(self):
        app = self.app.run()
        self.client.replies = [ConnectionError('offline')]
        app.chat_input[0].set_value('f(u)=sin(u), g(x)=x²').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['guided']['messages'], [])
        self.assertIn('pending_guided', app.session_state)
        self.client.replies = [verdict('CORRECTO')]
        app.button(key='retry').click().run()
        self.assertEqual(app.session_state['guided']['step'], 1)
        self.assertEqual(len(app.session_state['guided']['messages']), 2)
        self.assertNotIn('pending_guided', app.session_state)

    def test_completion_and_restart_remain_accessible(self):
        app = self.app.run()
        self.client.replies = [verdict('CORRECTO')] * 3
        for answer in ('f(u)=sin(u), g(x)=x²', 'cos(u)', '2x cos(x²)'):
            app.chat_input[0].set_value(answer).run()
        self.assertEqual(app.session_state['guided']['step'], 3)
        self.assertTrue(app.chat_input[0].disabled)
        app.button(key='reset').click().run()
        self.assertFalse(app.chat_input[0].disabled)
        self.assertFalse(app.exception)

    def test_missing_qwen_is_reported_before_loading_embeddings(self):
        with patch.object(self.client, 'list', return_value={'models': []}):
            app = self.app.run()
        self.assertFalse(app.exception)
        self.assertIn('ollama pull qwen2.5:3b', app.error[0].value)
        self.assertEqual(self.encoder.calls, [])
        app.run()
        self.assertFalse(app.error)
        self.assertEqual(len(app.chat_input), 1)

    def test_resource_failure_has_actionable_message(self):
        with patch('nikali.index.open_retriever', side_effect=ConnectionError('offline')):
            app = self.app.run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertIn('BGE-M3', app.error[0].value)


if __name__ == '__main__':
    unittest.main()
