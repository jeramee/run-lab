from __future__ import annotations
from pathlib import Path
import json

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
            json_errors.append(f"{path.relative_to(run_dir)}: {exc}")
    status = "passed_mechanical_checks" if not missing and not json_errors else "failed_mechanical_checks"
    return {
        "record_type": "verification_report",
        "verification_status": status,
        "missing": missing,
        "json_errors": json_errors,
        "authority_note": "RunLab verification is not scientific validation.",
    }
