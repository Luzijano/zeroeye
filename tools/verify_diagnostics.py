#!/usr/bin/env python3
"""Verification script for build diagnostics generation.

This script verifies that build.py properly generates the full build diagnostics,
including the entire logd file, even when the build fails due to work environment.

Usage:
    python3 tools/verify_diagnostics.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parent.parent
DIAGNOSTIC_DIR = ROOT / "diagnostic"


def run_build() -> Tuple[bool, str]:
    """Run build.py and capture output."""
    print("=" * 60)
    print("Running build.py...")
    print("=" * 60)

    try:
        result = subprocess.run(
            [sys.executable, "build.py"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Build timed out after 600 seconds"
    except Exception as e:
        return False, str(e)


def check_diagnostics() -> Tuple[bool, list[str]]:
    """Check if diagnostic files were generated."""
    print("\n" + "=" * 60)
    print("Checking diagnostic files...")
    print("=" * 60)

    if not DIAGNOSTIC_DIR.exists():
        return False, ["diagnostic/ directory does not exist"]

    files = list(DIAGNOSTIC_DIR.glob("build-*.logd")) + list(DIAGNOSTIC_DIR.glob("build-*.json"))

    if not files:
        return False, ["No diagnostic files found in diagnostic/"]

    found = []
    for f in sorted(files):
        size = f.stat().st_size
        found.append(f"{f.name} ({size} bytes)")
        print(f"  [OK] {f.name} ({size} bytes)")

    return True, found


def verify_json_metadata() -> Tuple[bool, list[str]]:
    """Verify JSON metadata files are valid."""
    print("\n" + "=" * 60)
    print("Verifying JSON metadata...")
    print("=" * 60)

    json_files = list(DIAGNOSTIC_DIR.glob("build-*.json"))

    if not json_files:
        return False, ["No JSON metadata files found"]

    errors = []
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check required fields
            required = ["generated_at", "commit", "total_modules", "passed", "failed", "modules"]
            missing = [k for k in required if k not in data]
            if missing:
                errors.append(f"{json_file.name}: missing fields {missing}")
            else:
                print(f"  [OK] {json_file.name}: valid JSON with required fields")
                print(f"    - generated_at: {data['generated_at']}")
                print(f"    - commit: {data['commit']}")
                print(f"    - modules: {data['total_modules']} total, {data['passed']} passed, {data['failed']} failed")

        except json.JSONDecodeError as e:
            errors.append(f"{json_file.name}: invalid JSON - {e}")
        except Exception as e:
            errors.append(f"{json_file.name}: error reading - {e}")

    return len(errors) == 0, errors


def verify_logd_files() -> Tuple[bool, list[str]]:
    """Verify logd files exist and have content."""
    print("\n" + "=" * 60)
    print("Verifying logd files...")
    print("=" * 60)

    logd_files = list(DIAGNOSTIC_DIR.glob("build-*.logd"))

    if not logd_files:
        return False, ["No logd files found"]

    errors = []
    for logd_file in logd_files:
        size = logd_file.stat().st_size
        if size == 0:
            errors.append(f"{logd_file.name}: file is empty")
        else:
            print(f"  [OK] {logd_file.name}: {size} bytes")

    return len(errors) == 0, errors


def main() -> int:
    """Main entry point."""
    print("=" * 60)
    print("Build Diagnostics Verification")
    print("=" * 60)
    print()

    # Run build
    build_ok, build_output = run_build()
    print(f"\nBuild result: {'PASS' if build_ok else 'FAIL'}")

    # Check diagnostics (should exist even if build failed)
    diag_ok, diag_files = check_diagnostics()

    # Verify JSON metadata
    json_ok, json_errors = verify_json_metadata()

    # Verify logd files
    logd_ok, logd_errors = verify_logd_files()

    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    print(f"  Build execution: {'PASS' if build_ok else 'FAIL'}")
    print(f"  Diagnostics generated: {'PASS' if diag_ok else 'FAIL'}")
    print(f"  JSON metadata valid: {'PASS' if json_ok else 'FAIL'}")
    print(f"  Logd files valid: {'PASS' if logd_ok else 'FAIL'}")

    all_ok = diag_ok and json_ok and logd_ok

    if all_ok:
        print("\n[OK] All diagnostics verified successfully!")
        print("\nDiagnostic files to include in PR:")
        for f in diag_files:
            print(f"  - diagnostic/{f}")
        return 0
    else:
        print("\n[FAIL] Diagnostics verification failed!")
        if not diag_ok:
            print(f"  Errors: {diag_files}")
        if not json_ok:
            print(f"  JSON errors: {json_errors}")
        if not logd_ok:
            print(f"  Logd errors: {logd_errors}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
