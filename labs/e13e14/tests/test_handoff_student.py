"""E13 handoff checks: the B side must hash the envelope before trusting it."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[2] / "e11e12"))
from handoff_a_to_b import make_handoff
import pipeline


def artifact(path, root, job_id):
    data = path.read_bytes()
    return {
        "uri": f"artifact://{job_id}/{path.relative_to(root).as_posix()}",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


class HandoffHashTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sha = "c" * 40
        self.job = "job-e13"
        self.trace = "trace-e13"
        inner = self.root / "incremental-report.json"
        inner.write_text('{"findings": []}\n')
        stage = {
            "schema_version": "e11e12-1",
            "kind": "incremental-check",
            "status": "SUCCEEDED",
            "commit": self.sha,
            "job_id": self.job,
            "trace_id": self.trace,
            "data": {"commit": self.sha, "findings": []},
            "artifacts": [artifact(inner, self.root, self.job)],
        }
        self.stage_path = self.root / "incremental-check.json"
        self.stage_path.write_text(json.dumps(stage) + "\n")
        result = {
            "schema_version": "e11e12-1",
            "status": "SUCCEEDED",
            "target_commit": self.sha,
            "job_id": self.job,
            "trace_id": self.trace,
            "stages": [
                {"name": "incremental-check",
                 "artifact": artifact(self.stage_path, self.root, self.job)}
            ],
        }
        self.result_path = self.root / "result.json"
        self.result_path.write_text(json.dumps(result) + "\n")

    def handoff(self, name="fixed-md.json"):
        path = self.root / name
        envelope = make_handoff(self.result_path, self.sha)
        path.write_text(json.dumps(envelope) + "\n", encoding="utf-8")
        return path

    def test_accepted_hash_matches_published_bytes(self):
        path = self.handoff()
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
        envelope = pipeline.load_artifact(path, expected)
        self.assertEqual(envelope["source_report"]["uri"],
                         f"artifact://{self.job}/incremental-check.json")
        self.assertEqual(envelope["source_report"]["sha256"],
                         hashlib.sha256(self.stage_path.read_bytes()).hexdigest())

    def test_tampered_envelope_is_rejected_before_parsing(self):
        path = self.handoff()
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
        path.write_text('{"findings": ["injected"]}\n', encoding="utf-8")
        with self.assertRaises(pipeline.Failure) as ctx:
            pipeline.load_artifact(path, expected)
        self.assertEqual(ctx.exception.code, "ARTIFACT_HASH_MISMATCH")

    def test_empty_hash_is_not_treated_as_missing(self):
        path = self.handoff()
        with self.assertRaises(pipeline.Failure) as ctx:
            pipeline.load_artifact(path, "")
        self.assertEqual(ctx.exception.code, "ARTIFACT_HASH_MISMATCH")


if __name__ == "__main__":
    unittest.main()
