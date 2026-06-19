#!/usr/bin/env python3
"""Compare Zeroeye diagnostic build metadata files.

The tool reports module additions/removals, status changes, duration deltas,
command changes, and artifact changes.  With --fail-on-regression it can be used
as a CI gate: the process exits non-zero only when the newer metadata regresses
relative to the baseline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PASS_STATUSES = {"PASS", "PASSED", "SUCCESS", "OK"}
FAIL_STATUSES = {"FAIL", "FAILED", "ERROR"}
MISSING_STATUS = "MISSING"


def load_metadata(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"metadata file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"metadata file is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"metadata root must be an object: {path}")
    return data


def normalize_status(value: Any) -> str:
    if value is None:
        return MISSING_STATUS
    text = str(value).strip().upper()
    return text or MISSING_STATUS


def is_pass(status: str) -> bool:
    return normalize_status(status) in PASS_STATUSES


def module_map(metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    modules = metadata.get("modules", [])
    if not isinstance(modules, list):
        raise SystemExit("metadata field 'modules' must be a list")
    mapped: dict[str, dict[str, Any]] = {}
    for index, module in enumerate(modules):
        if not isinstance(module, dict):
            raise SystemExit(f"module entry {index} must be an object")
        name = module.get("name")
        if not name:
            raise SystemExit(f"module entry {index} is missing a name")
        mapped[str(name)] = module
    return mapped


def command_value(module: dict[str, Any]) -> Any:
    for key in ("command", "build_command", "build_cmd", "cmd"):
        if key in module:
            return module[key]
    return None


def artifact_value(module: dict[str, Any]) -> Any:
    return module.get("artifact")


def duration_value(module: dict[str, Any]) -> float | None:
    for key in ("elapsed_seconds", "duration_seconds", "duration", "elapsed"):
        if key in module and module[key] is not None:
            try:
                return float(module[key])
            except (TypeError, ValueError):
                return None
    return None


def regression_reason(name: str, before: str, after: str) -> dict[str, str] | None:
    if is_pass(before) and normalize_status(after) in (FAIL_STATUSES | {MISSING_STATUS}):
        return {
            "module": name,
            "type": "status",
            "baseline": normalize_status(before),
            "new": normalize_status(after),
        }
    return None


def compare_metadata(baseline: dict[str, Any], newer: dict[str, Any]) -> dict[str, Any]:
    base_modules = module_map(baseline)
    new_modules = module_map(newer)
    base_names = set(base_modules)
    new_names = set(new_modules)
    all_names = sorted(base_names | new_names)

    additions: list[dict[str, Any]] = []
    removals: list[dict[str, Any]] = []
    status_changes: list[dict[str, Any]] = []
    duration_deltas: list[dict[str, Any]] = []
    command_changes: list[dict[str, Any]] = []
    artifact_changes: list[dict[str, Any]] = []
    regressions: list[dict[str, str]] = []

    for name in all_names:
        base = base_modules.get(name)
        new = new_modules.get(name)
        before_status = normalize_status(base.get("status") if base else None)
        after_status = normalize_status(new.get("status") if new else None)

        if base is None and new is not None:
            additions.append({"module": name, "status": after_status})
        elif base is not None and new is None:
            removals.append({"module": name, "baseline_status": before_status})
        elif before_status != after_status:
            status_changes.append({"module": name, "baseline": before_status, "new": after_status})

        regression = regression_reason(name, before_status, after_status)
        if regression:
            regressions.append(regression)

        if base is None or new is None:
            continue

        base_duration = duration_value(base)
        new_duration = duration_value(new)
        if base_duration is not None and new_duration is not None:
            delta = round(new_duration - base_duration, 3)
            if delta != 0:
                duration_deltas.append(
                    {
                        "module": name,
                        "baseline_seconds": base_duration,
                        "new_seconds": new_duration,
                        "delta_seconds": delta,
                    }
                )

        base_command = command_value(base)
        new_command = command_value(new)
        if base_command != new_command:
            command_changes.append({"module": name, "baseline": base_command, "new": new_command})

        base_artifact = artifact_value(base)
        new_artifact = artifact_value(new)
        if base_artifact != new_artifact:
            artifact_changes.append({"module": name, "baseline": base_artifact, "new": new_artifact})

    return {
        "baseline_commit": baseline.get("commit"),
        "new_commit": newer.get("commit"),
        "module_additions": additions,
        "module_removals": removals,
        "status_changes": status_changes,
        "duration_deltas": duration_deltas,
        "command_changes": command_changes,
        "artifact_changes": artifact_changes,
        "regressions": regressions,
    }


def print_text_summary(summary: dict[str, Any]) -> None:
    print("Diagnostic diff")
    if summary.get("baseline_commit") or summary.get("new_commit"):
        print(f"commits: {summary.get('baseline_commit') or 'unknown'} -> {summary.get('new_commit') or 'unknown'}")

    sections = [
        ("module additions", "module_additions"),
        ("module removals", "module_removals"),
        ("status changes", "status_changes"),
        ("duration deltas", "duration_deltas"),
        ("command changes", "command_changes"),
        ("artifact changes", "artifact_changes"),
    ]
    for title, key in sections:
        values = summary[key]
        print(f"{title}: {len(values)}")
        for value in values:
            print(f"  - {json.dumps(value, sort_keys=True)}")

    # JSON-compatible line intended for CI parsers and the regression gate.
    print(f"regressions: {json.dumps(summary['regressions'], sort_keys=True)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare diagnostic build metadata JSON files")
    parser.add_argument("baseline", type=Path, help="baseline diagnostic JSON metadata")
    parser.add_argument("newer", type=Path, help="newer diagnostic JSON metadata")
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="exit 1 when regressions are detected (pass -> fail/error/missing)",
    )
    parser.add_argument("--json", action="store_true", help="emit the full summary as JSON")
    args = parser.parse_args(argv)

    summary = compare_metadata(load_metadata(args.baseline), load_metadata(args.newer))
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print_text_summary(summary)

    if args.fail_on_regression and summary["regressions"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
