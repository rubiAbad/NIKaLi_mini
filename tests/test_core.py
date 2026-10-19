import json
import sys
import types
import unittest
from copy import deepcopy
from unittest.mock import patch, Mock

from evaluar_retrieval import evaluate as evaluate_retrieval, metrics
from golden_dataset import GOLDEN_DATASET, UNANSWERABLE_CASES
from nikali.config import make_embedder, settings
from nikali.rag import Retriever, corpus_digest, cosine, load_chunks, split_markdown
from nikali.tutor import PROBLEM, STEPS, evaluate, free_turn, guided_turn, new_session


class FakeClient:
    """Dobles de prueba: NO evalúan la calidad real de Qwen."""
    def __init__(self, replies=()):
        self.replies = list(replies)
        self.calls = []

    def list(self):
        return {"models": [{"model": "qwen2.5:3b"}]}

    def chat(self, **kwargs):
        self.calls.append(('chat', kwargs))
        if not self.replies:
            raise AssertionError('Falta una respuesta simulada')
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return {'message': {'content': reply}}


class FakeEncoder:
    """Sustituye BGE-M3 en pruebas; Qdrant sí se ejecuta realmente."""
    def __init__(self):
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((texts, kwargs))
        return [[1.0, float(len(t) % 7 + 1)] for t in texts]


def verdict(state):
    return json.dumps({'estado': state, 'motivo': 'Diagnóstico simulado'})


class TutorTests(unittest.TestCase):
    def setUp(self):
        self.session = new_session()
        self.client = FakeClient()
        self.retriever = Retriever(load_chunks(), encoder=FakeEncoder())

    def test_evaluator_gets_problem_reference_and_accepted_history(self):
        self.session['step'] = 1
        self.session['accepted'] = [{'step': 1, 'answer': 'f(u)=sin(u), g(x)=x²'}]
        self.session['messages'] = [{'role': 'user', 'content': '¿Respecto de u?'}]
        self.client.replies = [verdict('CORRECTO')]
        evaluate(self.client, 1, 'cos(u)', self.session)
        call = self.client.calls[-1][1]
        system = call['messages'][0]['content']
        self.assertIn(PROBLEM, system)
        self.assertIn(STEPS[1].reference, system)
        self.assertIn('g(x)=x²', system)
        self.assertEqual(call['messages'][1]['content'], '¿Respecto de u?')
        self.assertIn('format', call)

    def test_only_correct_advances_and_does_not_mutate_input(self):
        for state in ('CORRECTO', 'INCORRECTO', 'PARCIAL', 'PREGUNTA', 'REVISAR'):
            with self.subTest(state=state):
                self.client.replies = [verdict(state), 'Mira qué función está dentro.']
                before = deepcopy(self.session)
                result = guided_turn(self.client, self.retriever, self.session, 'mi intento')
                self.assertEqual(result['step'], int(state == 'CORRECTO'))
                self.assertEqual(self.session, before)
                self.assertEqual(len(result['messages']), 2)

    def test_invalid_output_never_advances(self):
        for raw in ('CORRECTO', 'NO CORRECTO', '{', '[]', '{}',
                    '{"estado":"NO CORRECTO","motivo":"x"}',
                    '{"estado":"CORRECTO","motivo":null}'):
            with self.subTest(raw=raw):
                self.client.replies = [raw]
                result = guided_turn(self.client, self.retriever, self.session, 'respuesta')
                self.assertEqual(result['step'], 0)
                self.assertEqual(result['debug']['verdict']['estado'], 'REVISAR')

    def test_error_does_not_change_progress_or_history(self):
        for replies in ([ConnectionError('offline')], [verdict('INCORRECTO'), ConnectionError('offline')]):
            self.client.replies = replies
            before = deepcopy(self.session)
            with self.assertRaises(ConnectionError):
                guided_turn(self.client, self.retriever, self.session, 'mi respuesta')
            self.assertEqual(before, self.session)

    def test_hint_gets_problem_and_history(self):
        self.session['messages'] = [{'role': 'user', 'content': 'No distingo las funciones'}]
        self.client.replies = [verdict('PREGUNTA'), 'Busca qué expresión se introduce al seno.']
        guided_turn(self.client, self.retriever, self.session, '¿Otra pista?')
        call = self.client.calls[-1][1]
        self.assertIn(PROBLEM, call['messages'][0]['content'])
        self.assertIn('No distingo las funciones', call['messages'][1]['content'])

    def test_final_step_and_restart(self):
        self.session['step'] = 2
        self.client.replies = [verdict('CORRECTO')]
        result = guided_turn(self.client, self.retriever, self.session, '2x cos(x²)')
        self.assertEqual(result['step'], 3)
        with self.assertRaises(ValueError):
            guided_turn(self.client, self.retriever, result, 'otra')
        self.assertEqual(new_session()['step'], 0)

    def test_free_chat_receives_history(self):
        self.session['messages'] = [{'role': 'user', 'content': '¿Qué es la interna?'}]
        self.client.replies = ['La función que se aplica primero.']
        result = free_turn(self.client, self.retriever, self.session, '¿Y en ese ejemplo?')
        self.assertEqual(self.client.calls[-1][1]['messages'][1]['content'], '¿Qué es la interna?')
        self.assertTrue(result['messages'][-1]['hits'])


class RetrievalTests(unittest.TestCase):
    def test_corpus_labels_and_partial_source(self):
        chunks = load_chunks()
        ids = {c.id for c in chunks}
        self.assertEqual(len(chunks), 2)
        self.assertEqual(len(ids), 2)
        self.assertEqual(sum(c.partial for c in chunks), 1)
        self.assertTrue(all(c.id.startswith("stewart:") for c in chunks))
        for item in GOLDEN_DATASET:
            self.assertTrue(set(item['ids_relevantes']) <= ids)
            self.assertTrue(item['ids_relevantes'])
        self.assertTrue(all(not c['ids_relevantes'] for c in UNANSWERABLE_CASES))
        self.assertEqual(len({c['id_pregunta'] for c in GOLDEN_DATASET + UNANSWERABLE_CASES}), 9)

    def test_splitter_preserves_math_and_ignores_code_headings(self):
        text = '# Uno\n$$x^2$$\n```python\n# comentario\n```\n## Dos\ntexto'
        chunks = split_markdown(text, 'x', 'fuente')
        self.assertEqual(len(chunks), 2)
        self.assertIn('$$x^2$$', chunks[0].text)
        self.assertIn('# comentario', chunks[0].text)
        self.assertEqual(chunks[1].id, 'x:dos')
        with self.assertRaises(ValueError):
            split_markdown('# Uno\na\n# Uno\nb', 'x', 'fuente')

    def test_invalid_embeddings_fail_explicitly(self):
        for a, b in (([], []), ([1], [1, 2]), ([0, 0], [1, 2]), ([float('nan')], [1])):
            with self.assertRaises(ValueError):
                cosine(a, b)
        self.assertAlmostEqual(cosine([1, 0], [1, 0]), 1)

    def test_search_ranking_uses_qdrant_and_same_encoder(self):
        encoder = FakeEncoder()
        chunks = load_chunks()[:2]
        with patch.object(encoder, 'encode', side_effect=[[[1, 0], [0, 1]], [[0, 1]]]) as encode:
            retriever = Retriever(chunks, encoder=encoder)
            hits = retriever.search('consulta', k=1)
        self.assertEqual(hits[0].chunk.id, chunks[1].id)
        self.assertAlmostEqual(hits[0].score, 1.0)
        self.assertEqual(retriever.qdrant.count('nikali').count, 2)
        self.assertEqual(encode.call_args_list[0].args[0], [c.text for c in chunks])
        self.assertEqual(encode.call_args_list[1].args[0], ['consulta'])

    def test_default_factory_requests_original_bge_model(self):
        constructor = Mock(return_value=FakeEncoder())
        module = types.ModuleType('sentence_transformers')
        module.SentenceTransformer = constructor
        with patch.dict(sys.modules, {'sentence_transformers': module}):
            encoder = make_embedder()
        constructor.assert_called_once_with('BAAI/bge-m3', device=settings.EMBED_DEVICE, local_files_only=False)
        self.assertIsInstance(encoder, FakeEncoder)

    def test_metrics_multiple_relevant_and_rank(self):
        result = metrics(['irrelevant', 'b', 'c'], ['b', 'c', 'd'], 3)
        self.assertEqual(result['hit_rate'], 1)
        self.assertAlmostEqual(result['precision'], 2/3)
        self.assertAlmostEqual(result['recall'], 2/3)
        self.assertEqual(result['mrr'], 0.5)
        self.assertEqual(metrics(['x'], ['b'], 1)['hit_rate'], 0)
        self.assertEqual(metrics(['b', 'b'], ['b'], 2)['precision'], 0.5)
        with self.assertRaises(ValueError):
            metrics(['x'], [], 1)

    def test_evaluation_rejects_unknown_labels_and_excessive_k(self):
        retriever = Retriever(load_chunks(), encoder=FakeEncoder())
        with self.assertRaises(ValueError):
            evaluate_retrieval(retriever, GOLDEN_DATASET, 7)
        bad = [{'id_pregunta': 'BAD', 'ids_relevantes': ['missing']}]
        with self.assertRaises(ValueError):
            evaluate_retrieval(retriever, bad, 1)
        result = evaluate_retrieval(retriever, GOLDEN_DATASET, 1)
        self.assertEqual(len(result['detalle']), 6)
        self.assertEqual(len(corpus_digest(retriever.chunks)), 64)


if __name__ == '__main__':
    unittest.main()
