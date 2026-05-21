from __future__ import annotations

from pathlib import Path, PurePosixPath
import json

from .constants import AUTHORITY_FLAGS, PLACEHOLDER_AUTHORITY_FLAGS
from .io import read_json, sha256_file, write_json

REQUIRED = [
    "inputs/query_job.json",
    "inputs/index_reference.json",
    "parameters/papermill_parameters.json",
    "records/execution_record.json",
    "records/retrieval_record.json",
    "records/source_citation_record.json",
    "records/context_pack.json",
    "context/context_pack.md",
    "records/environment_report.json",
    "records/replay_manifest.json",
    "records/artifact_manifest.json",
    "reports/report.md",
]

HTML_REPORT = "reports/report.html"

REQUIRED_RECORD_TYPES = {
    "inputs/query_job.json": "query_job",
    "inputs/index_reference.json": "index_reference",
    "parameters/papermill_parameters.json": "papermill_parameters",
    "records/execution_record.json": "execution_record",
    "records/retrieval_record.json": "retrieval_record",
    "records/source_citation_record.json": "source_citation_record",
    "records/context_pack.json": "context_pack",
    "records/environment_report.json": "environment_report",
    "records/replay_manifest.json": "replay_manifest",
    "records/artifact_manifest.json": "artifact_manifest",
}

REQUIRED_AUTHORITY_FLAG_RECORDS = [
    "inputs/query_job.json",
    "inputs/index_reference.json",
    "parameters/papermill_parameters.json",
    "records/execution_record.json",
    "records/retrieval_record.json",
    "records/source_citation_record.json",
    "records/context_pack.json",
    "records/environment_report.json",
    "records/replay_manifest.json",
    "records/artifact_manifest.json",
]

REQUIRED_FIELDS = {
    "inputs/query_job.json": [
        "record_type",
        "run_id",
        "job_id",
        "query",
        "index_ref",
        "citation_mode",
        "max_results",
        "source_job_path",
        "authority_flags",
        "integration_status",
        "placeholder_for",
        "placeholder_authority_flags",
    ],
    "inputs/index_reference.json": [
        "record_type",
        "run_id",
        "index_id",
        "backend",
        "source_index_path",
        "record_count",
        "selected_count",
        "records",
        "authority_flags",
        "integration_status",
        "placeholder_for",
        "placeholder_authority_flags",
    ],
    "parameters/papermill_parameters.json": [
        "record_type",
        "execution_mode",
        "query",
        "authority_flags",
        "integration_status",
        "placeholder_for",
        "placeholder_authority_flags",
    ],
    "records/execution_record.json": [
        "record_type",
        "run_id",
        "execution_status",
        "execution_backend",
        "executed_notebook",
        "authority_flags",
        "integration_status",
        "placeholder_for",
        "placeholder_authority_flags",
    ],
    "records/retrieval_record.json": [
        "record_type",
        "run_id",
        "backend",
        "query",
        "results",
        "authority_flags",
        "integration_status",
        "placeholder_for",
        "placeholder_authority_flags",
        "authority_note",
    ],
    "records/source_citation_record.json": [
        "record_type",
        "run_id",
        "citation_status",
        "citations",
        "authority_flags",
        "integration_status",
        "placeholder_for",
        "placeholder_authority_flags",
    ],
    "records/context_pack.json": [
        "record_type",
        "run_id",
        "context_file",
        "source_count",
        "authority_flags",
        "integration_status",
        "placeholder_for",
        "placeholder_authority_flags",
        "authority_note",
    ],
    "records/environment_report.json": [
        "record_type",
        "run_id",
        "captured_at",
        "environment_status",
        "raw_environment_dumped",
        "authority_flags",
        "integration_status",
        "placeholder_for",
        "placeholder_authority_flags",
    ],
    "records/replay_manifest.json": [
        "record_type",
        "run_id",
        "created_at",
        "replay_status",
        "replay_scope",
        "replay_artifacts",
        "replay_command",
        "authority_flags",
        "integration_status",
        "placeholder_for",
        "placeholder_authority_flags",
        "limitations",
    ],
    "records/artifact_manifest.json": [
        "record_type",
        "run_id",
        "created_at",
        "artifacts",
        "authority_flags",
    ],
}


CHECK_PASSED = "passed"
CHECK_FAILED = "failed"


def verify_run(run_dir: str | Path) -> dict:
    run_dir = Path(run_dir)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory does not exist: {run_dir}")
    if not run_dir.is_dir():
        raise NotADirectoryError(f"Run path is not a directory: {run_dir}")
    required = list(REQUIRED)
    if (run_dir / HTML_REPORT).exists():
        required.append(HTML_REPORT)

    missing = [rel for rel in required if not (run_dir / rel).exists()]

    parsed_json: dict[str, dict] = {}
    json_errors = []
    for path in run_dir.rglob("*.json"):
        rel = path.relative_to(run_dir).as_posix()
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                parsed_json[rel] = parsed
            else:
                json_errors.append(f"{rel}: top-level JSON value must be an object")
        except json.JSONDecodeError as exc:
            json_errors.append(f"{rel}: {exc}")

    record_type_errors = _check_record_types(parsed_json)
    required_field_errors = _check_required_fields(parsed_json)
    authority_flag_errors = _check_authority_flags(parsed_json)
    placeholder_flag_errors = _check_placeholder_flags(parsed_json)
    artifact_manifest_errors = _check_artifact_manifest_listings(parsed_json, required)
    artifact_hash_errors = _check_artifact_manifest_paths_and_hashes(run_dir, parsed_json)
    replay_artifact_errors = _check_replay_manifest_artifact_presence(run_dir, parsed_json)
    run_id_errors = _check_run_id_consistency(parsed_json)
    safe_path_errors = _check_safe_relative_packet_paths(parsed_json)

    checks = {
        "required_artifacts_present": _status(not missing),
        "json_parseable": _status(not json_errors),
        "required_record_types": _status(not record_type_errors),
        "required_fields_present": _status(not required_field_errors),
        "authority_flags_conservative": _status(not authority_flag_errors),
        "placeholder_integration_flags_conservative": _status(not placeholder_flag_errors),
        "artifact_manifest_lists_required_artifacts": _status(not artifact_manifest_errors),
        "artifact_manifest_paths_and_hashes": _status(not artifact_hash_errors),
        "replay_manifest_artifacts_exist": _status(not replay_artifact_errors),
        "record_run_ids_consistent": _status(not run_id_errors),
        "packet_paths_safe_relative_posix": _status(not safe_path_errors),
    }
    status = "passed" if all(value == CHECK_PASSED for value in checks.values()) else "failed"

    report = {
        "record_type": "verification_report",
        "verification_status": status,
        "checks": checks,
        "missing": missing,
        "json_errors": json_errors,
        "record_type_errors": record_type_errors,
        "required_field_errors": required_field_errors,
        "authority_flag_errors": authority_flag_errors,
        "placeholder_flag_errors": placeholder_flag_errors,
        "artifact_manifest_errors": artifact_manifest_errors,
        "artifact_hash_errors": artifact_hash_errors,
        "replay_artifact_errors": replay_artifact_errors,
        "run_id_errors": run_id_errors,
        "safe_path_errors": safe_path_errors,
        "authority_flags": dict(AUTHORITY_FLAGS),
        "authority_note": "RunLab verification is mechanical artifact-shape checking only, not scientific validation.",
    }

    report_path = run_dir / "records" / "verification_report.json"
    write_json(report_path, report)
    _record_verification_report_in_artifact_manifest(run_dir, report_path)

    return report


def _status(ok: bool) -> str:
    return CHECK_PASSED if ok else CHECK_FAILED


def _check_record_types(parsed_json: dict[str, dict]) -> list[str]:
    errors = []
    for rel, expected in REQUIRED_RECORD_TYPES.items():
        record = parsed_json.get(rel)
        if record is None:
            continue
        actual = record.get("record_type")
        if actual != expected:
            errors.append(f"{rel}: expected record_type {expected!r}, found {actual!r}")
    return errors


def _check_required_fields(parsed_json: dict[str, dict]) -> list[str]:
    errors = []
    for rel, fields in REQUIRED_FIELDS.items():
        record = parsed_json.get(rel)
        if record is None:
            continue
        for field in fields:
            if field not in record:
                errors.append(f"{rel}: missing required field {field!r}")
    return errors


def _check_run_id_consistency(parsed_json: dict[str, dict]) -> list[str]:
    run_ids = {
        rel: record.get("run_id")
        for rel, record in parsed_json.items()
        if "run_id" in record
    }

    expected_run_ids = {
        run_id
        for rel, run_id in run_ids.items()
        if rel != "records/verification_report.json" and run_id is not None
    }

    if not expected_run_ids:
        return []

    if len(expected_run_ids) > 1:
        expected = sorted(str(run_id) for run_id in expected_run_ids)
        return [f"run_id mismatch across packet records: {expected}"]

    expected = next(iter(expected_run_ids))
    errors = []

    for rel, run_id in sorted(run_ids.items()):
        if rel == "records/verification_report.json":
            continue
        if run_id != expected:
            errors.append(f"{rel}: expected run_id {expected!r}, found {run_id!r}")

    return errors
    

def _check_replay_manifest_artifact_presence(run_dir: Path, parsed_json: dict[str, dict]) -> list[str]:
    replay_manifest = parsed_json.get("records/replay_manifest.json")
    if replay_manifest is None:
        return []

    replay_artifacts = replay_manifest.get("replay_artifacts")
    if not isinstance(replay_artifacts, list):
        return ["records/replay_manifest.json: replay_artifacts must be a list"]

    errors = []
    for rel in replay_artifacts:
        if not isinstance(rel, str):
            errors.append("records/replay_manifest.json: replay_artifacts entries must be strings")
            continue
        if not (run_dir / rel).exists():
            errors.append(f"records/replay_manifest.json: replay artifact does not exist: {rel}")

    return errors


def _check_authority_flags(parsed_json: dict[str, dict]) -> list[str]:
    errors = []
    for rel in REQUIRED_AUTHORITY_FLAG_RECORDS:
        record = parsed_json.get(rel)
        if record is None:
            continue
        flags = record.get("authority_flags")
        if flags != AUTHORITY_FLAGS:
            errors.append(f"{rel}: authority_flags must preserve conservative defaults")
    return errors


def _check_placeholder_flags(parsed_json: dict[str, dict]) -> list[str]:
    errors = []
    for rel, record in sorted(parsed_json.items()):
        if record.get("integration_status") != "placeholder":
            continue
        if not record.get("placeholder_for"):
            errors.append(f"{rel}: placeholder records must declare placeholder_for")
        flags = record.get("placeholder_authority_flags")
        if flags != PLACEHOLDER_AUTHORITY_FLAGS:
            errors.append(f"{rel}: placeholder_authority_flags must preserve mechanical-only defaults")
    return errors


def _check_artifact_manifest_listings(parsed_json: dict[str, dict], required: list[str]) -> list[str]:
    manifest = parsed_json.get("records/artifact_manifest.json")
    if manifest is None:
        return []

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return ["records/artifact_manifest.json: artifacts must be a list"]

    listed_paths = {artifact.get("path") for artifact in artifacts if isinstance(artifact, dict)}
    required_listings = set(required) | {"records/artifact_manifest.json"}
    missing_listings = sorted(required_listings - listed_paths)

    return [f"records/artifact_manifest.json: missing listing for {rel}" for rel in missing_listings]


def _check_artifact_manifest_paths_and_hashes(run_dir: Path, parsed_json: dict[str, dict]) -> list[str]:
    manifest = parsed_json.get("records/artifact_manifest.json")
    if manifest is None:
        return []

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return []

    errors = []
    seen_paths = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            errors.append("records/artifact_manifest.json: each artifact entry must be an object")
            continue

        rel = artifact.get("path")
        if not isinstance(rel, str) or not rel:
            errors.append("records/artifact_manifest.json: artifact path must be a non-empty string")
            continue
        if rel in seen_paths:
            errors.append(f"records/artifact_manifest.json: duplicate artifact path {rel}")
        seen_paths.add(rel)

        path_check = _validate_relative_artifact_path(rel)
        if path_check is not None:
            errors.append(path_check)
            continue

        path = run_dir / rel
        if not path.exists():
            errors.append(f"records/artifact_manifest.json: listed artifact does not exist: {rel}")
            continue

        hash_record = artifact.get("hash")
        if hash_record is None:
            # Self-referential or explicitly non-hashed records are allowed only when declared.
            if "hash_status" not in artifact:
                errors.append(f"records/artifact_manifest.json: missing hash for {rel}")
            continue

        if not isinstance(hash_record, dict):
            errors.append(f"records/artifact_manifest.json: hash for {rel} must be an object")
            continue
        if hash_record.get("algorithm") != "sha256":
            errors.append(f"records/artifact_manifest.json: hash algorithm for {rel} must be sha256")
            continue
        expected = hash_record.get("value")
        actual = sha256_file(path)
        if expected != actual:
            errors.append(f"records/artifact_manifest.json: hash mismatch for {rel}")

    return errors


def _validate_relative_artifact_path(rel: str) -> str | None:
    path = PurePosixPath(rel)
    if path.is_absolute():
        return f"records/artifact_manifest.json: artifact path must be relative: {rel}"
    if any(part in {"", ".", ".."} for part in path.parts):
        return f"records/artifact_manifest.json: artifact path must not contain empty, current, or parent segments: {rel}"
    return None


def _check_safe_relative_packet_paths(parsed_json: dict[str, dict]) -> list[str]:
    errors = []

    manifest = parsed_json.get("records/artifact_manifest.json")
    if manifest is not None:
        artifacts = manifest.get("artifacts")
        if isinstance(artifacts, list):
            for artifact in artifacts:
                if not isinstance(artifact, dict):
                    continue
                path = artifact.get("path")
                if not isinstance(path, str):
                    errors.append("records/artifact_manifest.json: artifact path must be a string")
                    continue
                if not _is_safe_relative_posix_path(path):
                    errors.append(f"records/artifact_manifest.json: unsafe artifact path: {path}")

    replay_manifest = parsed_json.get("records/replay_manifest.json")
    if replay_manifest is not None:
        replay_artifacts = replay_manifest.get("replay_artifacts")
        if isinstance(replay_artifacts, list):
            for path in replay_artifacts:
                if not isinstance(path, str):
                    continue
                if not _is_safe_relative_posix_path(path):
                    errors.append(f"records/replay_manifest.json: unsafe replay artifact path: {path}")

    return errors


def _is_safe_relative_posix_path(path: str) -> bool:
    if not path:
        return False
    if "\\" in path:
        return False
    if path.startswith("/"):
        return False
    if ":" in path:
        return False

    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return False

    return True


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
