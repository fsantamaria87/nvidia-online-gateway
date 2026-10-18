"""Harness² contrastive gate unit tests. Only synthetic inputs; not app acceptance."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "experiment_gate.py"
spec = importlib.util.spec_from_file_location("gate", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "base.log").write_text("baseline")
        (self.root / "new.log").write_text("candidate")
        def e(path):
            return [{"path": path, "sha256": hashlib.sha256((self.root/path).read_bytes()).hexdigest()}]
        self.case = {
            "case_id": "synthetic", "data_kind": "synthetic_demo",
            "baseline": {"revision": "a", "environment": "same", "test_results": {"critical": True, "target": False}, "metrics": {"duration": 10}, "evidence": e("base.log")},
            "candidate": {"revision": "b", "environment": "same", "test_results": {"critical": True, "target": True}, "metrics": {"duration": 8}, "evidence": e("new.log")},
            "gates": {"required_tests": ["critical"], "target_tests": ["target"], "metric_limits": {"duration": {"max_regression_pct": 0}}}
        }

    def run_gate(self):
        return gate.evaluate(self.case, self.root)

    def test_synthetic_only(self):
        self.assertEqual(self.run_gate()["status"], "DEMO_ONLY")

    def test_real_requires_review(self):
        self.case["data_kind"] = "real"
        self.assertEqual(self.run_gate()["status"], "ELIGIBLE_FOR_REVIEW")

    def test_critical_failure_blocked(self):
        self.case["candidate"]["test_results"]["critical"] = False
        self.assertEqual(self.run_gate()["status"], "BLOCK")

    def test_target_regression_blocked(self):
        self.case["baseline"]["test_results"]["target"] = True
        self.case["candidate"]["test_results"]["target"] = False
        self.assertEqual(self.run_gate()["status"], "BLOCK")

    def test_metric_regression_blocked(self):
        self.case["candidate"]["metrics"]["duration"] = 12
        self.assertEqual(self.run_gate()["status"], "BLOCK")

    def test_no_gain_blocked(self):
        self.case["candidate"]["test_results"]["target"] = False
        self.case["candidate"]["metrics"]["duration"] = 10
        self.assertEqual(self.run_gate()["status"], "BLOCK")

    def test_different_environment_invalid(self):
        self.case["candidate"]["environment"] = "other"
        with self.assertRaises(ValueError): self.run_gate()

    def test_modified_log_invalid(self):
        self.case["baseline"]["evidence"][0]["sha256"] = "0" * 64
        with self.assertRaises(ValueError): self.run_gate()

    def test_path_traversal_invalid(self):
        self.case["baseline"]["evidence"][0]["path"] = "../outside"
        with self.assertRaises(ValueError): self.run_gate()

    def test_nonfinite_metric_invalid(self):
        self.case["candidate"]["metrics"]["duration"] = float("nan")
        with self.assertRaises(ValueError): self.run_gate()

    def test_missing_test_invalid(self):
        del self.case["candidate"]["test_results"]["critical"]
        with self.assertRaises(ValueError): self.run_gate()


if __name__ == "__main__":
    unittest.main()
