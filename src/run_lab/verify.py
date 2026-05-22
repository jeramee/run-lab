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
        "run_id",
        "execution_mode",
        "execution_backend",
        "optional_dependency_boundary",
        "notebook_execution_policy",
        "notebook_template",
        "executed_notebook",
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
        "optional_dependency_boundary",
        "notebook_execution_policy",
        "notebook_template",
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
    notebook_stub_errors = _check_executed_notebook_stub_shape(run_dir, parsed_json)
    notebook_template_errors = _check_notebook_template_stub_shape(run_dir, parsed_json)
    optional_dependency_boundary_errors = _check_optional_dependency_boundary(parsed_json)
    notebook_execution_policy_errors = _check_notebook_execution_disabled_policy(run_dir, parsed_json)

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
        "executed_notebook_stub_shape": _status(not notebook_stub_errors),
        "notebook_template_stub_shape": _status(not notebook_template_errors),
        "optional_papermill_dependency_boundary_conservative": _status(not optional_dependency_boundary_errors),
        "papermill_execution_disabled_by_default": _status(not notebook_execution_policy_errors),
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
        "notebook_stub_errors": notebook_stub_errors,
        "notebook_template_errors": notebook_template_errors,
        "optional_dependency_boundary_errors": optional_dependency_boundary_errors,
        "notebook_execution_policy_errors": notebook_execution_policy_errors,
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



def _check_optional_dependency_boundary(parsed_json: dict[str, dict]) -> list[str]:
    errors = []
    required_records = [
        "parameters/papermill_parameters.json",
        "records/execution_record.json",
    ]

    for rel in required_records:
        record = parsed_json.get(rel)
        if record is None:
            continue

        boundary = record.get("optional_dependency_boundary")
        if not isinstance(boundary, dict):
            errors.append(f"{rel}: optional_dependency_boundary must be an object")
            continue

        if boundary.get("required_for_v0_1") is not False:
            errors.append(f"{rel}: optional_dependency_boundary.required_for_v0_1 must be false")
        if boundary.get("execution_enabled_by_default") is not False:
            errors.append(f"{rel}: optional_dependency_boundary.execution_enabled_by_default must be false")
        if boundary.get("real_execution_allowed") is not False:
            errors.append(f"{rel}: optional_dependency_boundary.real_execution_allowed must be false")
        if boundary.get("dependency_probe_method") != "importlib.util.find_spec":
            errors.append(f"{rel}: optional_dependency_boundary.dependency_probe_method must be importlib.util.find_spec")

        dependencies = boundary.get("dependencies")
        if not isinstance(dependencies, dict):
            errors.append(f"{rel}: optional_dependency_boundary.dependencies must be an object")
            continue

        for dependency_name in ("papermill", "nbclient"):
            dependency = dependencies.get(dependency_name)
            if not isinstance(dependency, dict):
                errors.append(f"{rel}: optional_dependency_boundary.dependencies.{dependency_name} must be an object")
                continue

            if dependency.get("module") != dependency_name:
                errors.append(f"{rel}: optional_dependency_boundary.dependencies.{dependency_name}.module must be {dependency_name!r}")
            if not isinstance(dependency.get("available"), bool):
                errors.append(f"{rel}: optional_dependency_boundary.dependencies.{dependency_name}.available must be boolean")
            if dependency.get("used") is not False:
                errors.append(f"{rel}: optional_dependency_boundary.dependencies.{dependency_name}.used must be false")

    return errors


def _check_notebook_execution_disabled_policy(run_dir: Path, parsed_json: dict[str, dict]) -> list[str]:
    errors = []

    policy_records: list[tuple[str, object]] = []
    for rel in (
        "parameters/papermill_parameters.json",
        "records/execution_record.json",
    ):
        record = parsed_json.get(rel)
        if record is None:
            continue
        policy_records.append((rel, record.get("notebook_execution_policy")))

    execution_record = parsed_json.get("records/execution_record.json")
    if execution_record is not None:
        executed_notebook = execution_record.get("executed_notebook")
        if isinstance(executed_notebook, str) and _is_safe_relative_posix_path(executed_notebook):
            notebook_path = run_dir / executed_notebook
            if notebook_path.exists():
                try:
                    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
                    metadata = notebook.get("metadata") if isinstance(notebook, dict) else None
                    if isinstance(metadata, dict):
                        policy_records.append((f"{executed_notebook}: metadata", metadata.get("notebook_execution_policy")))
                except json.JSONDecodeError:
                    pass

    for rel, policy in policy_records:
        if not isinstance(policy, dict):
            errors.append(f"{rel}: notebook_execution_policy must be an object")
            continue

        if policy.get("policy_status") != "disabled_by_default":
            errors.append(f"{rel}: notebook_execution_policy.policy_status must be 'disabled_by_default'")
        if policy.get("execution_disabled_by_default") is not True:
            errors.append(f"{rel}: notebook_execution_policy.execution_disabled_by_default must be true")
        if policy.get("real_execution_permitted") is not False:
            errors.append(f"{rel}: notebook_execution_policy.real_execution_permitted must be false")
        if policy.get("actual_notebook_execution") is not False:
            errors.append(f"{rel}: notebook_execution_policy.actual_notebook_execution must be false")
        if policy.get("papermill_execution_requested") is not False:
            errors.append(f"{rel}: notebook_execution_policy.papermill_execution_requested must be false")
        if policy.get("papermill_execution_performed") is not False:
            errors.append(f"{rel}: notebook_execution_policy.papermill_execution_performed must be false")
        if policy.get("nbclient_execution_performed") is not False:
            errors.append(f"{rel}: notebook_execution_policy.nbclient_execution_performed must be false")
        if policy.get("override_supported") is not False:
            errors.append(f"{rel}: notebook_execution_policy.override_supported must be false")

    return errors



def _check_notebook_template_stub_shape(run_dir: Path, parsed_json: dict[str, dict]) -> list[str]:
    execution_record = parsed_json.get("records/execution_record.json")
    if execution_record is None:
        return []

    notebook_template = execution_record.get("notebook_template")
    if not isinstance(notebook_template, str) or not notebook_template:
        return ["records/execution_record.json: notebook_template must be a non-empty string"]
    if not _is_safe_relative_posix_path(notebook_template):
        return [f"records/execution_record.json: notebook_template must be a safe relative POSIX path: {notebook_template}"]
    if not notebook_template.startswith("notebooks/templates/"):
        return [f"records/execution_record.json: notebook_template must point under notebooks/templates/: {notebook_template}"]

    workspace_root = run_dir.parent.parent if run_dir.parent.name == "runs" else run_dir.parent
    template_path = workspace_root / notebook_template
    if not template_path.exists():
        return [f"records/execution_record.json: notebook_template does not exist in workspace: {notebook_template}"]

    try:
        template = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{notebook_template}: invalid notebook template JSON: {exc}"]

    if not isinstance(template, dict):
        return [f"{notebook_template}: notebook template JSON must be an object"]

    errors = []
    if template.get("nbformat") != 4:
        errors.append(f"{notebook_template}: nbformat must be 4")
    if not isinstance(template.get("nbformat_minor"), int):
        errors.append(f"{notebook_template}: nbformat_minor must be an integer")

    metadata = template.get("metadata")
    if not isinstance(metadata, dict):
        errors.append(f"{notebook_template}: metadata must be an object")
    else:
        if metadata.get("run_lab_template") is not True:
            errors.append(f"{notebook_template}: metadata.run_lab_template must be true")
        if metadata.get("integration_status") != "placeholder":
            errors.append(f"{notebook_template}: metadata.integration_status must be 'placeholder'")
        if metadata.get("placeholder_for") != "future_papermill_notebook_execution":
            errors.append(f"{notebook_template}: metadata.placeholder_for must be future_papermill_notebook_execution")
        if metadata.get("actual_notebook_execution") is not False:
            errors.append(f"{notebook_template}: metadata.actual_notebook_execution must be false")
        if metadata.get("papermill_invoked") is not False:
            errors.append(f"{notebook_template}: metadata.papermill_invoked must be false")
        if metadata.get("nbclient_invoked") is not False:
            errors.append(f"{notebook_template}: metadata.nbclient_invoked must be false")

    cells = template.get("cells")
    if not isinstance(cells, list) or not cells:
        errors.append(f"{notebook_template}: cells must be a non-empty list")
        return errors

    has_markdown = False
    has_code = False
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            errors.append(f"{notebook_template}: cell {index} must be an object")
            continue
        cell_type = cell.get("cell_type")
        if cell_type == "markdown":
            has_markdown = True
        elif cell_type == "code":
            has_code = True
            if cell.get("execution_count") is not None:
                errors.append(f"{notebook_template}: code cell {index} execution_count must be null for template stubs")
            if cell.get("outputs") != []:
                errors.append(f"{notebook_template}: code cell {index} outputs must be empty for template stubs")
        else:
            errors.append(f"{notebook_template}: cell {index} has unsupported cell_type {cell_type!r}")
        if "source" not in cell:
            errors.append(f"{notebook_template}: cell {index} missing source")
        if not isinstance(cell.get("metadata"), dict):
            errors.append(f"{notebook_template}: cell {index} metadata must be an object")

    if not has_markdown:
        errors.append(f"{notebook_template}: template must include at least one markdown cell")
    if not has_code:
        errors.append(f"{notebook_template}: template must include at least one code cell")

    return errors

def _check_executed_notebook_stub_shape(run_dir: Path, parsed_json: dict[str, dict]) -> list[str]:
    execution_record = parsed_json.get("records/execution_record.json")
    if execution_record is None:
        return []

    executed_notebook = execution_record.get("executed_notebook")
    if not isinstance(executed_notebook, str) or not executed_notebook:
        return ["records/execution_record.json: executed_notebook must be a non-empty string"]
    if not _is_safe_relative_posix_path(executed_notebook):
        return [f"records/execution_record.json: executed_notebook must be a safe relative POSIX path: {executed_notebook}"]

    notebook_path = run_dir / executed_notebook
    if not notebook_path.exists():
        return [f"records/execution_record.json: executed_notebook does not exist: {executed_notebook}"]

    try:
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{executed_notebook}: invalid notebook JSON: {exc}"]

    errors = []
    if not isinstance(notebook, dict):
        return [f"{executed_notebook}: notebook JSON must be an object"]

    if notebook.get("nbformat") != 4:
        errors.append(f"{executed_notebook}: nbformat must be 4")
    if not isinstance(notebook.get("nbformat_minor"), int):
        errors.append(f"{executed_notebook}: nbformat_minor must be an integer")

    cells = notebook.get("cells")
    if not isinstance(cells, list) or not cells:
        errors.append(f"{executed_notebook}: cells must be a non-empty list")
        return errors

    metadata = notebook.get("metadata")
    if not isinstance(metadata, dict):
        errors.append(f"{executed_notebook}: metadata must be an object")
    else:
        if metadata.get("run_lab_execution") != "placeholder":
            errors.append(f"{executed_notebook}: metadata.run_lab_execution must be 'placeholder'")
        if metadata.get("actual_notebook_execution") is not False:
            errors.append(f"{executed_notebook}: metadata.actual_notebook_execution must be false")
        if metadata.get("papermill_invoked") is not False:
            errors.append(f"{executed_notebook}: metadata.papermill_invoked must be false")
        if metadata.get("nbclient_invoked") is not False:
            errors.append(f"{executed_notebook}: metadata.nbclient_invoked must be false")

    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            errors.append(f"{executed_notebook}: cell {index} must be an object")
            continue
        cell_type = cell.get("cell_type")
        if cell_type not in {"markdown", "code"}:
            errors.append(f"{executed_notebook}: cell {index} has unsupported cell_type {cell_type!r}")
        if "source" not in cell:
            errors.append(f"{executed_notebook}: cell {index} missing source")
        if not isinstance(cell.get("metadata"), dict):
            errors.append(f"{executed_notebook}: cell {index} metadata must be an object")
        if cell_type == "code":
            if cell.get("execution_count") is not None:
                errors.append(f"{executed_notebook}: code cell {index} execution_count must be null for placeholder stubs")
            if cell.get("outputs") != []:
                errors.append(f"{executed_notebook}: code cell {index} outputs must be empty for placeholder stubs")

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
