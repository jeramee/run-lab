from __future__ import annotations

from pathlib import Path
import json

from .io import read_json, sha256_file, write_json

REQUIRED = [
    "inputs/query_job.json",
    "inputs/index_reference.json",
    "parameters/papermill_parameters.json",
    "records/retrieval_record.json",
    "records/source_citations.json",
    "context/context_pack.md",
    "records/notebook_run_record.json",
    "records/environment_report.json",
    "records/replay_manifest.json",
    "records/artifact_manifest.json",
]


def verify_run(run_dir: str | Path) -> dict:
    run_dir = Path(run_dir)
    missing = [rel for rel in REQUIRED if not (run_dir / rel).exists()]

    json_errors = []
    for path in run_dir.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            json_errors.append(f"{path.relative_to(run_dir).as_posix()}: {exc}")

    status = "pass" if not missing and not json_errors else "fail"

    report = {
        "record_type": "verification_report",
        "verification_status": status,
        "checks": {
            "required_artifacts_present": "pass" if not missing else "fail",
            "json_parseable": "pass" if not json_errors else "fail",
        },
        "missing": missing,
        "json_errors": json_errors,
        "authority_note": "RunLab verification is mechanical artifact-shape checking only, not scientific validation.",
    }

    report_path = run_dir / "records" / "verification_report.json"
    write_json(report_path, report)
    _record_verification_report_in_artifact_manifest(run_dir, report_path)

    return report


def _record_verification_report_in_artifact_manifest(run_dir: Path, report_path: Path) -> None:
    manifest_path = run_dir / "records" / "artifact_manifest.json"
    if not manifest_path.exists():
        return

    manifest = read_json(manifest_path)
    artifacts = [
        artifact
        for artifact in manifest.get("artifacts", [])
        if artifact.get("path") != "records/verification_report.json"
    ]

    artifacts.append({
        "path": report_path.relative_to(run_dir).as_posix(),
        "hash": {
            "algorithm": "sha256",
            "value": sha256_file(report_path),
        },
    })

    manifest["artifacts"] = sorted(artifacts, key=lambda artifact: artifact.get("path", ""))
    write_json(manifest_path, manifest)