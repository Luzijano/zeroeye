#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "diagnostic_diff.py"


def metadata(*modules):
    return {"commit": "test", "modules": list(modules)}


def module(name, status):
    return {"name": name, "status": status, "elapsed_seconds": 1.0, "artifact": None}


class DiagnosticDiffRegressionGateTest(unittest.TestCase):
    def run_diff(self, baseline, newer, *extra_args):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            baseline_path = tmp_path / "baseline.json"
            newer_path = tmp_path / "newer.json"
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            newer_path.write_text(json.dumps(newer), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(TOOL), str(baseline_path), str(newer_path), *extra_args],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
            )

    def test_pass_to_fail_is_regression_and_fails_gate(self):
        result = self.run_diff(
            metadata(module("backend", "PASS")),
            metadata(module("backend", "FAIL")),
            "--fail-on-regression",
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"module": "backend"', result.stdout)
        self.assertIn('"new": "FAIL"', result.stdout)

    def test_fail_to_pass_is_not_regression(self):
        result = self.run_diff(
            metadata(module("backend", "FAIL")),
            metadata(module("backend", "PASS")),
            "--fail-on-regression",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("regressions: []", result.stdout)

    def test_unchanged_failure_is_not_regression(self):
        result = self.run_diff(
            metadata(module("backend", "FAIL")),
            metadata(module("backend", "FAIL")),
            "--fail-on-regression",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("regressions: []", result.stdout)

    def test_missing_previously_passing_module_is_regression(self):
        result = self.run_diff(
            metadata(module("backend", "PASS"), module("frontend", "PASS")),
            metadata(module("frontend", "PASS")),
            "--fail-on-regression",
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"module": "backend"', result.stdout)
        self.assertIn('"new": "MISSING"', result.stdout)

    def test_without_gate_regression_keeps_success_exit(self):
        result = self.run_diff(metadata(module("backend", "PASS")), metadata(module("backend", "FAIL")))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("regressions:", result.stdout)


if __name__ == "__main__":
    unittest.main()
