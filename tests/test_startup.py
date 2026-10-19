"""Regresiones de configuración y diagnóstico; no ejecutan modelos."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from ollama import ListResponse
from nikali.config import CHAT_MODEL, EMBED_MODEL, ROOT, settings
from nikali.preflight import StartupError, check_ollama
from nikali.rag import load_chunks


class StartupTests(unittest.TestCase):
    def test_root_config_is_same_instance_and_models_are_fixed(self):
        from config import settings as legacy
        self.assertIs(legacy, settings)
        self.assertEqual(CHAT_MODEL, 'qwen2.5:3b')
        self.assertEqual(EMBED_MODEL, 'BAAI/bge-m3')

    def test_offline_and_missing_model_give_different_instructions(self):
        client = Mock()
        client.list.side_effect = ConnectionError('offline')
        with self.assertRaisesRegex(StartupError, 'ollama serve'):
            check_ollama(client)
        client.list.side_effect = None
        client.list.return_value = {'models': [{'model': 'otro:3b'}]}
        with self.assertRaisesRegex(StartupError, 'ollama pull qwen2.5:3b'):
            check_ollama(client)

    def test_actual_ollama_response_schema_is_supported(self):
        client = Mock()
        client.list.return_value = ListResponse(models=[{'model': 'qwen2.5:3b'}])
        self.assertEqual(check_ollama(client), 'qwen2.5:3b')

    def test_missing_corpus_identifies_file(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / 'fragmento_corregido.md'
            with patch('nikali.rag.CORPUS_PATH', missing):
                with self.assertRaisesRegex(FileNotFoundError, 'fragmento_corregido.md'):
                    load_chunks()

    def test_paths_work_from_another_directory(self):
        env = {**os.environ, 'PYTHONPATH': str(ROOT)}
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, '-c', 'import json; from nikali.rag import load_chunks; print(json.dumps([c.id for c in load_chunks()]))'],
                cwd=directory, env=env, capture_output=True, text=True, check=True)
        self.assertEqual(len(json.loads(result.stdout)), 2)


if __name__ == '__main__':
    unittest.main()
