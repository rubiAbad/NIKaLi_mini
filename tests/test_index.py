"""El corpus nunca se codifica al consultar; el paquete y Qdrant sobreviven reinicios."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from nikali.config import CORPUS_PATH, EMBED_DIMENSION, ROOT
from nikali.index import (CHUNKER_VERSION, PROFILE, SCHEMA_VERSION, PreparedIndexError,
                          canonical_digest, load_prepared, open_retriever, prepare_index, source_digest)
from nikali.rag import corpus_digest, load_chunks


def fixture():
    chunks = load_chunks()
    vectors = [[1.0 if j == i else 0.0 for j in range(EMBED_DIMENSION)] for i in range(len(chunks))]
    data = {'schema_version': SCHEMA_VERSION, 'chunker_version': CHUNKER_VERSION,
            'embedding': dict(PROFILE), 'source': {'path': CORPUS_PATH.relative_to(ROOT).as_posix(),
                                                  'sha256': source_digest(CORPUS_PATH)},
            'chunks': [asdict(c) for c in chunks], 'vectors': vectors,
            'corpus_sha256': corpus_digest(chunks)}
    return data


def write_bundle(path, data):
    data = deepcopy(data)
    data['sha256'] = canonical_digest(data)
    path.write_text(json.dumps(data), encoding='utf-8')


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / 'index.json'
        self.data = fixture()
        write_bundle(self.path, self.data)

    def test_loading_never_chunks_or_loads_embedding_model(self):
        with patch('nikali.index.load_chunks', side_effect=AssertionError('No chunking')), \
             patch('nikali.index.make_embedder', side_effect=AssertionError('No models')):
            prepared = load_prepared(self.path)
            self.assertEqual(len(prepared.chunks), 2)
            self.assertEqual(prepare_index(self.path).digest, prepared.digest)

    def test_persistent_reopen_does_not_insert_or_encode_documents(self):
        prepared = load_prepared(self.path)
        encoder = Mock()
        encoder.encode.return_value = [self.data['vectors'][1]]
        with open_retriever(prepared, cache_root=self.root, encoder=encoder) as retriever:
            encoder.encode.assert_not_called()
            self.assertEqual(retriever.search('consulta')[0].chunk.id, prepared.chunks[1].id)
        with patch('qdrant_client.QdrantClient.upsert', side_effect=AssertionError('No reinserción')):
            with open_retriever(prepared, cache_root=self.root, encoder=encoder) as reopened:
                self.assertEqual(reopened.search('otra consulta')[0].chunk.id, prepared.chunks[1].id)
        self.assertEqual([c.args[0] for c in encoder.encode.call_args_list], [['consulta'], ['otra consulta']])

    def test_query_model_loads_only_when_needed(self):
        prepared = load_prepared(self.path)
        encoder = Mock()
        encoder.encode.return_value = [self.data['vectors'][0]]
        with patch('nikali.rag.make_embedder', return_value=encoder) as factory:
            with open_retriever(prepared, cache_root=self.root) as retriever:
                factory.assert_not_called()
                retriever.search('pregunta')
                factory.assert_called_once()
                retriever.search('seguimiento')
                factory.assert_called_once()

    def test_web_and_cli_can_open_at_same_time(self):
        prepared = load_prepared(self.path)
        with open_retriever(prepared, cache_root=self.root, consumer='web') as web:
            with open_retriever(prepared, cache_root=self.root, consumer='cli') as cli:
                self.assertEqual(web.qdrant.count('nikali').count, cli.qdrant.count('nikali').count)
            with self.assertRaisesRegex(RuntimeError, 'Cierra otra instancia'):
                open_retriever(prepared, cache_root=self.root, consumer='web')

    def test_changed_source_rejected_but_windows_newlines_accepted(self):
        source = self.root / 'fragment.md'
        text = CORPUS_PATH.read_text(encoding='utf-8')
        source.write_bytes(text.replace('\n', '\r\n').encode('utf-8'))
        load_prepared(self.path, source=source)
        source.write_text(text + '\nContenido nuevo', encoding='utf-8')
        with self.assertRaisesRegex(PreparedIndexError, 'Markdown cambió'):
            load_prepared(self.path, source=source)

    def test_incompatible_model_and_bad_vectors_are_rejected(self):
        for mutate in (
            lambda d: d['embedding'].update(model='otro'),
            lambda d: d['embedding'].update(revision='otra-revision'),
            lambda d: d['vectors'].pop(),
            lambda d: d['vectors'][0].pop(),
            lambda d: d['vectors'][0].__setitem__(0, 0),
            lambda d: d['chunks'][1].update(id=d['chunks'][0]['id']),
        ):
            data = deepcopy(self.data)
            mutate(data)
            write_bundle(self.path, data)
            with self.assertRaises(PreparedIndexError):
                load_prepared(self.path)

    def test_corruption_and_missing_file_never_trigger_automatic_preparation(self):
        data = json.loads(self.path.read_text())
        data['vectors'][0][0] = 0.5
        self.path.write_text(json.dumps(data))
        with patch('nikali.index.make_embedder', side_effect=AssertionError('No models')):
            with self.assertRaisesRegex(PreparedIndexError, 'checksum'):
                load_prepared(self.path)
            self.path.unlink()
            with self.assertRaisesRegex(PreparedIndexError, 'preparar_indice.py'):
                load_prepared(self.path)

    def test_failed_rebuild_preserves_previous_bundle(self):
        before = self.path.read_bytes()
        with patch('nikali.index.make_embedder', side_effect=ConnectionError('offline')):
            with self.assertRaises(ConnectionError):
                prepare_index(self.path, recreate=True)
        self.assertEqual(before, self.path.read_bytes())

    def test_partial_import_reloads_saved_vectors_without_model(self):
        prepared = load_prepared(self.path)
        with open_retriever(prepared, cache_root=self.root) as retriever:
            retriever.qdrant.delete('nikali', points_selector=[0])
        (self.root / prepared.digest / 'cli' / 'ready.txt').unlink()
        with patch('nikali.rag.make_embedder', side_effect=AssertionError('No models')):
            with open_retriever(prepared, cache_root=self.root) as recovered:
                self.assertEqual(recovered.qdrant.count('nikali').count, 2)


if __name__ == '__main__':
    unittest.main()
