import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pipeline
import server

class Contracts(unittest.TestCase):
    def report(self):return {'schema_version':'e11e12-1','kind':'incremental-check','commit':'a'*40,'status':'SUCCEEDED'}
    def test_accept_current_report(self):pipeline.check_envelope(self.report(),'a'*40,'incremental-check')
    def test_reject_old_commit(self):
        with self.assertRaisesRegex(pipeline.Failure,'another commit'):pipeline.check_envelope(self.report(),'b'*40)
    def test_reject_schema(self):
        r=self.report();r['schema_version']='old'
        with self.assertRaises(pipeline.Failure):pipeline.check_envelope(r,'a'*40)
    def test_reject_failed_upstream(self):
        r=self.report();r['status']='FAILED'
        with self.assertRaises(pipeline.Failure):pipeline.check_envelope(r,'a'*40)
    def test_reject_wrong_artifact_kind(self):
        with self.assertRaises(pipeline.Failure):pipeline.check_envelope(self.report(),'a'*40,'fixed-md')
    def test_artifact_uses_relative_uri_and_content_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'x.json';p.write_text('{}')
            a=pipeline.artifact(p,root,'job-1');self.assertEqual(a['uri'],'artifact://job-1/x.json');self.assertEqual(len(a['sha256']),64)
    def test_existing_evidence_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'keep').write_text('keep')
            with self.assertRaises(pipeline.Failure):pipeline.execute({},root)
            self.assertEqual((root/'keep').read_text(),'keep')
    def test_changed_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.json';p.write_text('{}')
            with self.assertRaises(pipeline.Failure):pipeline.load_artifact(p,'0'*64)
    def test_same_key_same_request_same_job(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);store=server.Store(root/'jobs')
            request={'mode':'e11-a','repo':str(pipeline.ROOT/'data/p'),'base':'a','target':'b'}
            with patch.object(store.pool,'submit'):
                one=store.submit(request,'same');two=store.submit(request,'same')
                self.assertEqual(one['job_id'],two['job_id'])
                changed=dict(request,target='c')
                with self.assertRaisesRegex(ValueError,'IDEMPOTENCY_CONFLICT'):store.submit(changed,'same')
            store.pool.shutdown()
    def test_api_rejects_repo_outside_data(self):
        with tempfile.TemporaryDirectory() as d:
            store=server.Store(Path(d)/'jobs')
            with self.assertRaises(ValueError):store.submit({'mode':'e11-a','repo':str(Path(d)),'base':'a','target':'b'},'k')
            store.pool.shutdown()

    def test_selective_request_refreshes_only_affected_target(self):
        with tempfile.TemporaryDirectory() as d:
            from lab import commit, fixture, run
            root = Path(d)
            project = root / 'project'
            fixture(project)
            base = run(['git', 'rev-parse', 'HEAD'], project).strip()
            header = project / 'config.h'
            header.write_text(header.read_text() + '#include "extra.h"\n')
            target = commit(project, 'Add transitive include')
            request = {
                'mode': 'e11-a', 'repo': str(project), 'base': base,
                'target': target, 'selective': True,
            }
            out = root / 'evidence'
            result = pipeline.execute(request, out)
            self.assertEqual(result['status'], 'SUCCEEDED', result.get('error'))
            report = json.loads((out / 'incremental-report.json').read_text())
            self.assertEqual(report['refreshed'], ['main.o'])
            self.assertEqual(report['reused'], ['helper.o'])
            self.assertIn('extra.h', report['actual']['main.o'])
            self.assertIn(['MISSING', 'main.o', 'extra.h'], report['added'])

    def test_e11b_rejects_tampered_fixed_report_sha256(self):
        with tempfile.TemporaryDirectory() as d:
            from lab import commit, fixture, run, scan
            root = Path(d)
            project = root / 'project'
            fixture(project)
            base = run(['git', 'rev-parse', 'HEAD'], project).strip()
            (project / 'main.c').write_text('#include "extra.h"\n' + (project / 'main.c').read_text())
            target = commit(project, 'Add include')
            report_path = root / 'fixed-md.json'
            envelope = {
                'schema_version': 'e11e12-1', 'kind': 'fixed-md',
                'status': 'SUCCEEDED', 'commit': target, 'data': scan(project),
            }
            report_path.write_text(json.dumps(envelope) + '\n')
            orig_sha = pipeline.hashlib.sha256(report_path.read_bytes()).hexdigest()
            report_path.write_bytes(report_path.read_bytes() + b'\n')
            cand = root / 'candidate.Dockerfile'
            cand.write_text('FROM scratch\n')
            request = {
                'mode': 'e11-b', 'repo': str(project), 'base': base, 'target': target,
                'candidate': str(cand), 'fixed_report': str(report_path),
                'fixed_report_sha256': orig_sha,
            }
            def fake_draft(_target, _cand, draft_out, *_a, **_kw):
                draft_out.mkdir(parents=True, exist_ok=True)
                (draft_out / 'result.json').write_text('{"status":"SUCCEEDED"}\n')
                return {'status': 'SUCCEEDED'}
            with patch('draft.autobuild.auto_build', side_effect=fake_draft):
                result = pipeline.execute(request, root / 'out')
            self.assertEqual(result['status'], 'FAILED')
            self.assertEqual(result['error']['code'], 'ARTIFACT_HASH_MISMATCH')

if __name__=='__main__':unittest.main()
