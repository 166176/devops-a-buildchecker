"""Student contract tests for the E11-E12 integration interface."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pipeline
import server


class StudentContracts(unittest.TestCase):
    def envelope(self, **overrides):
        report = {'schema_version': 'e11e12-1', 'kind': 'incremental-check',
                  'commit': 'a' * 40, 'status': 'SUCCEEDED'}
        report.update(overrides)
        return report

    def test_artifact_hash_and_size_match_file_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'nested').mkdir()
            target = root / 'nested' / 'report.json'
            target.write_text('{"k": 1}', encoding='utf-8')
            entry = pipeline.artifact(target, root, 'job-student')
            self.assertEqual(entry['uri'], 'artifact://job-student/nested/report.json')
            self.assertEqual(entry['sha256'], hashlib.sha256(target.read_bytes()).hexdigest())
            self.assertEqual(entry['bytes'], target.stat().st_size)

    def test_missing_schema_version_is_rejected(self):
        report = self.envelope()
        del report['schema_version']
        with self.assertRaisesRegex(pipeline.Failure, 'e11e12-1'):
            pipeline.check_envelope(report, 'a' * 40, 'incremental-check')

    def test_blank_idempotency_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = server.Store(Path(directory) / 'jobs')
            try:
                request = {'mode': 'e11-a', 'repo': str(pipeline.ROOT / 'data/p'),
                           'base': 'a', 'target': 'b'}
                with self.assertRaises(ValueError):
                    store.submit(request, '   ')
            finally:
                store.pool.shutdown()

    def test_unfinished_job_marked_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'jobs'
            job = root / 'job-restarted'
            job.mkdir(parents=True)
            state = {'schema_version': 'e11e12-1', 'job_id': 'job-restarted',
                     'status': 'RUNNING', 'idempotency_key': 'restart-key',
                     'request_hash': 'deadbeef'}
            (job / 'state.json').write_text(json.dumps(state), encoding='utf-8')
            store = server.Store(root)
            try:
                saved = json.loads((job / 'state.json').read_text(encoding='utf-8'))
                self.assertEqual(saved['status'], 'FAILED')
                self.assertEqual(saved['error']['code'], 'SERVER_RESTARTED')
                self.assertEqual(store.keys['restart-key'], ('deadbeef', 'job-restarted'))
            finally:
                store.pool.shutdown()


if __name__ == '__main__':
    unittest.main()
