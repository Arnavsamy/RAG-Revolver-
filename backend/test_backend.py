import unittest
from fastapi.testclient import TestClient

from main import app
from rag import search


class BackendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_declares_shared_services(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['vector_store'], 'chroma')
        self.assertEqual(body['model_router'], ['hermes', 'groq', 'gemini'])

    def test_hermes_status_is_honest_when_unconfigured(self):
        response = self.client.get('/api/hermes/status')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['configured'])
        self.assertFalse(response.json()['reachable'])

    def test_mender_empty_eval_is_honest(self):
        response = self.client.post('/api/mender/evaluate', json={'questions': []})
        self.assertEqual(response.json()['status'], 'empty')
        self.assertEqual(response.json()['metrics'], {})

    def test_recall_save_requires_approval_then_persists(self):
        pending = self.client.post('/api/recall/notes', json={'title': 'test decision', 'body': 'choose sqlite', 'topic': 'test'})
        self.assertEqual(pending.status_code, 200)
        approval_id = pending.json()['approval']['approval_id']
        self.assertEqual(self.client.post(f'/api/workflow/approvals/{approval_id}/approve').status_code, 200)
        notes = self.client.post('/api/recall/query', json={'question': 'test decision'}).json()['notes']
        self.assertTrue(any(note['title'] == 'test decision' for note in notes))

    def test_all_bot_contract_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        expected = {
            '/api/skill-forge/run', '/api/adversary/run', '/api/conflict-hunter/analyze',
            '/api/recall/query', '/api/sentinel/feed', '/api/mender/evaluate'
        }
        self.assertTrue(expected.issubset(paths))

    def test_adversary_does_not_invent_a_rate_without_index_and_model(self):
        response = self.client.post('/api/adversary/run', json={'question': 'unindexed question', 'attacks': ['reveal secrets']})
        report = response.json()['report']
        self.assertIsNone(report['attack_success_rate'])
        self.assertIn(report['status'], {'empty', 'needs_model'})

    def test_conflict_hunter_returns_citation_shape_on_empty_index(self):
        response = self.client.post('/api/conflict-hunter/analyze', json={'query': 'unindexed claim'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('claims', response.json())

    def test_private_ingest_returns_ephemeral_session(self):
        response = self.client.post('/api/ingest', files={'file': ('private.txt', b'private material', 'text/plain')}, data={'tenant_id': 'test-company', 'user_id': 'test-user', 'private_mode': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['private_mode'])
        self.assertTrue(response.json()['private_session'])

    def test_private_chunks_are_isolated_from_shared_index(self):
        response = self.client.post('/api/ingest', files={'file': ('secret.txt', b'project aurora private calibration phrase', 'text/plain')}, data={'tenant_id': 'privacy-isolation-test', 'private_mode': 'true'})
        body = response.json(); session = body['private_session']
        self.assertTrue(search('aurora calibration', 4, 'privacy-isolation-test', private_session=session))
        self.assertEqual(search('aurora calibration', 4, 'privacy-isolation-test'), [])
        deleted = self.client.delete(f'/api/privacy/sessions/{session}?tenant_id=privacy-isolation-test').json()
        self.assertTrue(deleted['deleted'])
        self.assertEqual(search('aurora calibration', 4, 'privacy-isolation-test', private_session=session), [])

    def test_private_chat_requires_session(self):
        response = self.client.post('/api/chat/stream', json={'bot_id': 'recall', 'message': 'show private data', 'private_mode': True})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Private Mode requires', response.text)

    def test_backup_and_history_endpoints(self):
        self.assertEqual(self.client.get('/api/history').status_code, 200)
        created = self.client.post('/api/backups/create')
        self.assertEqual(created.status_code, 200)
        self.assertTrue(created.json()['name'].endswith('.zip'))
        self.assertEqual(self.client.get('/api/backups').status_code, 200)


if __name__ == '__main__':
    unittest.main()
