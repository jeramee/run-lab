from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from run_lab import run_notebook_placeholder
from run_lab.workspace import init_workspace, inspect_workspace
from run_lab.runner import run_demo
from run_lab.verify import verify_run
from run_lab.replay import inspect_replay_manifest


def test_run_lab_workspace_run_verify(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    state = inspect_workspace(workspace)
    assert state["exists"]

    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "demo")
    result = verify_run(run_dir)

    assert result["verification_status"] == "passed"
    assert result["checks"]["required_record_types"] == "passed"
    assert result["checks"]["required_fields_present"] == "passed"
    assert result["checks"]["authority_flags_conservative"] == "passed"
    assert result["checks"]["placeholder_integration_flags_conservative"] == "passed"
    assert result["checks"]["artifact_manifest_lists_required_artifacts"] == "passed"
    assert result["checks"]["artifact_manifest_paths_and_hashes"] == "passed"
    assert result["checks"]["replay_manifest_artifacts_exist"] == "passed"
    assert result["checks"]["record_run_ids_consistent"] == "passed"
    assert result["checks"]["packet_paths_safe_relative_posix"] == "passed"    

    assert (run_dir / "reports" / "report.md").exists()
    assert (run_dir / "reports" / "report.html").exists()
    assert (run_dir / "records" / "execution_record.json").exists()
    assert (run_dir / "records" / "source_citation_record.json").exists()
    assert (run_dir / "records" / "context_pack.json").exists()

    verification_report = run_dir / "records" / "verification_report.json"
    assert verification_report.exists()

    artifact_manifest_text = (run_dir / "records" / "artifact_manifest.json").read_text(encoding="utf-8")
    assert "records/replay_manifest.json" in artifact_manifest_text
    assert "records/artifact_manifest.json" in artifact_manifest_text
    assert "records/verification_report.json" in artifact_manifest_text
    assert "reports/report.md" in artifact_manifest_text

    replay_report = inspect_replay_manifest(run_dir / "records" / "replay_manifest.json")
    assert replay_report["record_type"] == "replay_inspection_report"
    assert replay_report["run_id"] == "demo"
    assert replay_report["replay_status"] == "not_run"
    assert "inputs/query_job.json" in replay_report["replay_artifacts"]
    assert "reports/report.md" in replay_report["replay_artifacts"]
    assert replay_report["authority_flags"]["correctness_proven"] is False

    assert not (run_dir / "records" / "lab_run_record.json").exists()
    assert not (run_dir / "records" / "notebook_run_record.json").exists()


def test_cli_commands_smoke_preserve_packet_boundary(tmp_path):
    workspace = tmp_path / "workspace"
    env = {**os.environ, "PYTHONPATH": "src"}

    init_result = subprocess.run(
        [sys.executable, "-m", "run_lab", "init", str(workspace)],
        check=True,
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
    )
    assert str(workspace) in init_result.stdout

    inspect_result = subprocess.run(
        [sys.executable, "-m", "run_lab", "inspect", str(workspace)],
        check=True,
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
    )
    assert "rag_literature_demo.json" in inspect_result.stdout

    run_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "run_lab",
            "run",
            "--workspace",
            str(workspace),
            "--query-job",
            "jobs/rag_literature_demo.json",
            "--output-prefix",
            "cli_demo",
        ],
        check=True,
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
    )
    assert "cli_demo" in run_result.stdout

    run_dir = workspace / "runs" / "cli_demo"
    verify_result = subprocess.run(
        [sys.executable, "-m", "run_lab", "verify", str(run_dir)],
        check=True,
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
    )
    verify_payload = json.loads(verify_result.stdout)
    assert verify_payload["verification_status"] == "passed"
    assert verify_payload["checks"]["artifact_manifest_paths_and_hashes"] == "passed"

    replay_result = subprocess.run(
        [sys.executable, "-m", "run_lab", "replay", str(run_dir / "records" / "replay_manifest.json")],
        check=True,
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
    )
    replay_payload = json.loads(replay_result.stdout)
    assert replay_payload["record_type"] == "replay_inspection_report"
    assert replay_payload["authority_flags"]["correctness_proven"] is False


def test_verify_fails_when_required_record_missing(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "missing_record_demo")
    (run_dir / "records" / "execution_record.json").unlink()

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["required_artifacts_present"] == "failed"
    assert "records/execution_record.json" in result["missing"]
    assert (run_dir / "records" / "verification_report.json").exists()


def test_verify_fails_when_manifest_hash_mismatch(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "hash_mismatch_demo")
    report_path = run_dir / "reports" / "report.md"
    report_path.write_text(report_path.read_text(encoding="utf-8") + "\nmutated after manifest\n", encoding="utf-8")

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["artifact_manifest_paths_and_hashes"] == "failed"
    assert any("hash mismatch for reports/report.md" in error for error in result["artifact_hash_errors"])


def test_verify_fails_when_required_field_missing(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "missing_field_demo")

    query_job_path = run_dir / "inputs" / "query_job.json"
    query_job = json.loads(query_job_path.read_text(encoding="utf-8"))
    query_job.pop("query")
    query_job_path.write_text(json.dumps(query_job, indent=2), encoding="utf-8")

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["required_fields_present"] == "failed"
    assert any("inputs/query_job.json: missing required field 'query'" in error for error in result["required_field_errors"])
    
    
def test_verify_can_run_twice_without_self_breaking_manifest(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "verify_twice_demo")

    first = verify_run(run_dir)
    second = verify_run(run_dir)

    assert first["verification_status"] == "passed"
    assert second["verification_status"] == "passed"
    assert second["checks"]["artifact_manifest_paths_and_hashes"] == "passed"
    assert second["checks"]["artifact_manifest_lists_required_artifacts"] == "passed"


def test_verify_fails_when_manifested_artifact_hash_changes(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "tamper_demo")

    report_path = run_dir / "reports" / "report.md"
    if not report_path.exists():
        report_path = run_dir / "reports" / "rendered_report.md"

    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "\n\nTampered after manifest creation.\n",
        encoding="utf-8",
    )

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["artifact_manifest_paths_and_hashes"] == "failed"
    assert any("hash mismatch" in error for error in result["artifact_hash_errors"])
    
    
def test_cli_verify_exit_code_contract(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "cli_verify_demo")

    passed = subprocess.run(
        [sys.executable, "-m", "run_lab", "verify", str(run_dir)],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert passed.returncode == 0
    assert '"verification_status": "passed"' in passed.stdout

    report_path = run_dir / "reports" / "report.md"
    if not report_path.exists():
        report_path = run_dir / "reports" / "rendered_report.md"

    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "\n\nTampered after manifest creation.\n",
        encoding="utf-8",
    )

    failed = subprocess.run(
        [sys.executable, "-m", "run_lab", "verify", str(run_dir)],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert failed.returncode != 0
    assert '"verification_status": "failed"' in failed.stdout


def test_run_packet_uses_official_report_artifact_names(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "official_report_names_demo")

    assert (run_dir / "reports" / "report.md").exists()
    assert (run_dir / "reports" / "report.html").exists()

    result = verify_run(run_dir)

    assert result["verification_status"] == "passed"

    artifact_manifest = json.loads(
        (run_dir / "records" / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    artifact_paths = {
        artifact.get("path")
        for artifact in artifact_manifest["artifacts"]
        if isinstance(artifact, dict)
    }

    assert "reports/report.md" in artifact_paths
    assert "reports/report.html" in artifact_paths


def test_persisted_verification_report_contract(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "verification_report_contract_demo")

    result = verify_run(run_dir)

    report_path = run_dir / "records" / "verification_report.json"
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["record_type"] == "verification_report"
    assert report["verification_status"] == result["verification_status"]
    assert report["verification_status"] in {"passed", "failed", "passed_with_warnings", "not_run"}
    assert isinstance(report["checks"], dict)
    assert report["checks"]["required_artifacts_present"] == "passed"
    assert report["checks"]["json_parseable"] == "passed"
    assert report["authority_flags"]["correctness_proven"] is False
    assert report["authority_flags"]["repo_mutated"] is False
    assert report["authority_flags"]["state_promoted"] is False
    assert report["authority_flags"]["source_control_touched"] is False
    assert "mechanical" in report["authority_note"].lower()
    assert "scientific validation" in report["authority_note"].lower()

    artifact_manifest = json.loads(
        (run_dir / "records" / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    verification_entries = [
        artifact
        for artifact in artifact_manifest["artifacts"]
        if artifact.get("path") == "records/verification_report.json"
    ]

    assert len(verification_entries) == 1
    assert verification_entries[0]["hash"]["algorithm"] == "sha256"
    assert verification_entries[0]["hash"]["value"]


def test_verify_fails_when_replay_manifest_lists_missing_artifact(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "missing_replay_artifact_demo")

    replay_manifest_path = run_dir / "records" / "replay_manifest.json"
    replay_manifest = json.loads(replay_manifest_path.read_text(encoding="utf-8"))
    replay_manifest["replay_artifacts"].append("reports/does_not_exist.md")
    replay_manifest_path.write_text(json.dumps(replay_manifest, indent=2), encoding="utf-8")

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["replay_manifest_artifacts_exist"] == "failed"
    assert any("reports/does_not_exist.md" in error for error in result["replay_artifact_errors"])
    
    
def test_verify_fails_when_record_run_id_does_not_match_packet(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "run_id_demo")

    retrieval_record_path = run_dir / "records" / "retrieval_record.json"
    retrieval_record = json.loads(retrieval_record_path.read_text(encoding="utf-8"))
    retrieval_record["run_id"] = "wrong_run_id"
    retrieval_record_path.write_text(json.dumps(retrieval_record, indent=2), encoding="utf-8")

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["record_run_ids_consistent"] == "failed"
    assert result["run_id_errors"]
    assert any("wrong_run_id" in error for error in result["run_id_errors"])


def test_verify_fails_when_artifact_manifest_uses_unsafe_path(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "unsafe_path_demo")

    artifact_manifest_path = run_dir / "records" / "artifact_manifest.json"
    artifact_manifest = json.loads(artifact_manifest_path.read_text(encoding="utf-8"))
    artifact_manifest["artifacts"].append({
        "path": "../outside_packet.txt",
        "hash": {
            "algorithm": "sha256",
            "value": "not-a-real-hash",
        },
    })
    artifact_manifest_path.write_text(json.dumps(artifact_manifest, indent=2), encoding="utf-8")

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["packet_paths_safe_relative_posix"] == "failed"
    assert any("../outside_packet.txt" in error for error in result["safe_path_errors"])
    
    
def test_verify_fails_when_replay_manifest_uses_unsafe_path(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "unsafe_replay_path_demo")

    replay_manifest_path = run_dir / "records" / "replay_manifest.json"
    replay_manifest = json.loads(replay_manifest_path.read_text(encoding="utf-8"))
    replay_manifest["replay_artifacts"].append(r"C:\absolute\outside_packet.txt")
    replay_manifest_path.write_text(json.dumps(replay_manifest, indent=2), encoding="utf-8")

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["packet_paths_safe_relative_posix"] == "failed"
    assert any("C:\\absolute\\outside_packet.txt" in error for error in result["safe_path_errors"])


def test_cli_replay_inspects_manifest_without_claiming_success(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "cli_replay_demo")

    replay_manifest_path = run_dir / "records" / "replay_manifest.json"

    completed = subprocess.run(
        [sys.executable, "-m", "run_lab", "replay", str(replay_manifest_path)],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert '"record_type": "replay_inspection_report"' in completed.stdout
    assert '"run_id": "cli_replay_demo"' in completed.stdout
    assert '"replay_status": "not_run"' in completed.stdout
    assert "Replay metadata is not replay success." in completed.stdout
    assert "replay_success" not in completed.stdout
    assert "validated" not in completed.stdout.lower()
    assert "certified" not in completed.stdout.lower()
    assert "approved" not in completed.stdout.lower()


def test_cli_run_creates_packet_that_cli_verify_accepts(tmp_path):
    workspace = tmp_path / "workspace"
    env = {**os.environ, "PYTHONPATH": "src"}

    init_completed = subprocess.run(
        [sys.executable, "-m", "run_lab", "init", str(workspace)],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert init_completed.returncode == 0

    run_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "run_lab",
            "run",
            "--workspace",
            str(workspace),
            "--query-job",
            "jobs/rag_literature_demo.json",
            "--output-prefix",
            "cli_run_contract_demo",
        ],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert run_completed.returncode == 0

    run_dir = workspace / "runs" / "cli_run_contract_demo"
    assert run_dir.exists()
    assert (run_dir / "records" / "artifact_manifest.json").exists()
    assert (run_dir / "records" / "replay_manifest.json").exists()
    assert (run_dir / "reports" / "report.md").exists()
    assert (run_dir / "reports" / "report.html").exists()

    verify_completed = subprocess.run(
        [sys.executable, "-m", "run_lab", "verify", str(run_dir)],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert verify_completed.returncode == 0
    assert '"verification_status": "passed"' in verify_completed.stdout
    assert '"required_artifacts_present": "passed"' in verify_completed.stdout
    assert '"artifact_manifest_paths_and_hashes": "passed"' in verify_completed.stdout


def test_cli_inspect_reports_workspace_without_authority_claims(tmp_path):
    workspace = tmp_path / "workspace"
    env = {**os.environ, "PYTHONPATH": "src"}

    init_completed = subprocess.run(
        [sys.executable, "-m", "run_lab", "init", str(workspace)],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert init_completed.returncode == 0

    inspect_completed = subprocess.run(
        [sys.executable, "-m", "run_lab", "inspect", str(workspace)],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert inspect_completed.returncode == 0

    inspect_report = json.loads(inspect_completed.stdout)

    assert inspect_report["record_type"] == "workspace_inspection_report"
    assert inspect_report["workspace"] == str(workspace)
    assert inspect_report["authority_flags"]["correctness_proven"] is False
    assert inspect_report["authority_flags"]["repo_mutated"] is False
    assert inspect_report["authority_flags"]["state_promoted"] is False
    assert inspect_report["authority_flags"]["source_control_touched"] is False

    assert "validated" not in inspect_completed.stdout.lower()
    assert "certified" not in inspect_completed.stdout.lower()
    assert "approved" not in inspect_completed.stdout.lower()
    assert inspect_report["authority_flags"]["state_promoted"] is False
    assert '"state_promoted": true' not in inspect_completed.stdout.lower()
    assert "scientifically_valid" not in inspect_completed.stdout.lower()


def test_cli_run_refuses_to_silently_overwrite_existing_packet(tmp_path):
    workspace = tmp_path / "workspace"
    env = {**os.environ, "PYTHONPATH": "src"}

    init_completed = subprocess.run(
        [sys.executable, "-m", "run_lab", "init", str(workspace)],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert init_completed.returncode == 0

    first_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "run_lab",
            "run",
            "--workspace",
            str(workspace),
            "--query-job",
            "jobs/rag_literature_demo.json",
            "--output-prefix",
            "overwrite_guard_demo",
        ],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert first_run.returncode == 0

    run_dir = workspace / "runs" / "overwrite_guard_demo"
    marker_path = run_dir / "manual_marker.txt"
    marker_path.write_text("must not be deleted by second run", encoding="utf-8")

    second_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "run_lab",
            "run",
            "--workspace",
            str(workspace),
            "--query-job",
            "jobs/rag_literature_demo.json",
            "--output-prefix",
            "overwrite_guard_demo",
        ],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert second_run.returncode != 0
    assert marker_path.exists()
    assert marker_path.read_text(encoding="utf-8") == "must not be deleted by second run"
    
    
def test_cli_run_fails_when_query_job_is_missing_without_creating_packet(tmp_path):
    workspace = tmp_path / "workspace"
    env = {**os.environ, "PYTHONPATH": "src"}

    init_completed = subprocess.run(
        [sys.executable, "-m", "run_lab", "init", str(workspace)],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert init_completed.returncode == 0

    run_completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "run_lab",
            "run",
            "--workspace",
            str(workspace),
            "--query-job",
            "jobs/does_not_exist.json",
            "--output-prefix",
            "missing_query_job_demo",
        ],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert run_completed.returncode != 0
    assert not (workspace / "runs" / "missing_query_job_demo").exists()
    assert "does_not_exist.json" in run_completed.stderr or "does_not_exist.json" in run_completed.stdout


def test_cli_verify_fails_cleanly_when_run_dir_is_missing(tmp_path):
    missing_run_dir = tmp_path / "workspace" / "runs" / "missing_run"

    completed = subprocess.run(
        [sys.executable, "-m", "run_lab", "verify", str(missing_run_dir)],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert not missing_run_dir.exists()
    combined_output = completed.stdout + completed.stderr
    assert "missing_run" in combined_output


def test_cli_verify_fails_cleanly_when_run_path_is_file(tmp_path):
    fake_run_path = tmp_path / "not_a_run_dir.json"
    fake_run_path.write_text("{}", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "-m", "run_lab", "verify", str(fake_run_path)],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert fake_run_path.exists()
    assert fake_run_path.is_file()

    combined_output = completed.stdout + completed.stderr
    assert "not_a_run_dir.json" in combined_output


def test_cli_replay_fails_cleanly_when_manifest_is_missing(tmp_path):
    missing_manifest = tmp_path / "workspace" / "runs" / "missing_run" / "records" / "replay_manifest.json"

    completed = subprocess.run(
        [sys.executable, "-m", "run_lab", "replay", str(missing_manifest)],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert not missing_manifest.exists()

    combined_output = completed.stdout + completed.stderr
    assert "replay_manifest.json" in combined_output
    assert "replay_success" not in combined_output.lower()
    assert "validated" not in combined_output.lower()
    assert "certified" not in combined_output.lower()
    assert "approved" not in combined_output.lower()


def test_notebook_template_placeholder_contract_is_explicit(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "notebook_placeholder_contract_demo")

    execution_record = json.loads(
        (run_dir / "records" / "execution_record.json").read_text(encoding="utf-8")
    )
    papermill_parameters = json.loads(
        (run_dir / "parameters" / "papermill_parameters.json").read_text(encoding="utf-8")
    )
    executed_notebook = json.loads(
        (run_dir / "executed" / "notebook_placeholder_contract_demo.executed.ipynb").read_text(encoding="utf-8")
    )

    assert execution_record["record_type"] == "execution_record"
    assert execution_record["run_id"] == "notebook_placeholder_contract_demo"
    assert execution_record["notebook_template"] == "notebooks/templates/literature_evidence_runner.ipynb"
    assert execution_record["executed_notebook"] == "executed/notebook_placeholder_contract_demo.executed.ipynb"
    assert execution_record["execution_backend"] == "placeholder_papermill"
    assert execution_record["integration_status"] == "placeholder"
    assert execution_record["placeholder_for"] == "future_papermill_notebook_execution"

    assert papermill_parameters["record_type"] == "papermill_parameters"
    assert papermill_parameters["run_id"] == "notebook_placeholder_contract_demo"
    assert papermill_parameters["notebook_template"] == execution_record["notebook_template"]
    assert papermill_parameters["executed_notebook"] == execution_record["executed_notebook"]
    assert papermill_parameters["execution_backend"] == "placeholder_papermill"
    assert papermill_parameters["integration_status"] == "placeholder"
    assert papermill_parameters["placeholder_for"] == "future_papermill_notebook_execution"

    assert executed_notebook["metadata"]["run_lab_execution"] == "placeholder"
    assert executed_notebook["metadata"]["notebook_template"] == execution_record["notebook_template"]
    assert executed_notebook["metadata"]["execution_backend"] == "placeholder_papermill"
    assert executed_notebook["metadata"]["integration_status"] == "placeholder"
    assert executed_notebook["metadata"]["placeholder_for"] == "future_papermill_notebook_execution"

    result = verify_run(run_dir)

    assert result["verification_status"] == "passed"
    assert result["checks"]["required_fields_present"] == "passed"
    assert result["checks"]["placeholder_integration_flags_conservative"] == "passed"


def test_real_nbformat_notebook_stub_shape_is_mechanically_verified(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "nbformat_stub_demo")

    notebook_path = run_dir / "executed" / "nbformat_stub_demo.executed.ipynb"
    executed_notebook = json.loads(notebook_path.read_text(encoding="utf-8"))

    assert executed_notebook["nbformat"] == 4
    assert executed_notebook["nbformat_minor"] == 5
    assert executed_notebook["metadata"]["actual_notebook_execution"] is False
    assert executed_notebook["metadata"]["papermill_invoked"] is False
    assert executed_notebook["metadata"]["nbclient_invoked"] is False
    assert executed_notebook["metadata"]["kernelspec"]["name"] == "python3"
    assert executed_notebook["metadata"]["language_info"]["name"] == "python"
    assert len(executed_notebook["cells"]) == 2
    assert executed_notebook["cells"][0]["cell_type"] == "markdown"
    assert executed_notebook["cells"][1]["cell_type"] == "code"
    assert executed_notebook["cells"][1]["execution_count"] is None
    assert executed_notebook["cells"][1]["outputs"] == []
    assert "ACTUAL_NOTEBOOK_EXECUTION = False" in "".join(executed_notebook["cells"][1]["source"])

    result = verify_run(run_dir)

    assert result["verification_status"] == "passed"
    assert result["checks"]["executed_notebook_stub_shape"] == "passed"


def test_verify_fails_when_notebook_stub_contains_execution_outputs(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "executed_output_stub_demo")

    notebook_path = run_dir / "executed" / "executed_output_stub_demo.executed.ipynb"
    executed_notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    executed_notebook["cells"][1]["execution_count"] = 1
    executed_notebook["cells"][1]["outputs"] = [{"output_type": "stream", "name": "stdout", "text": "not allowed"}]
    notebook_path.write_text(json.dumps(executed_notebook, indent=2), encoding="utf-8")

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["executed_notebook_stub_shape"] == "failed"
    assert any("execution_count must be null" in error for error in result["notebook_stub_errors"])
    assert any("outputs must be empty" in error for error in result["notebook_stub_errors"])


def test_optional_papermill_dependency_boundary_is_recorded_without_execution(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "optional_dependency_demo")

    execution_record = json.loads(
        (run_dir / "records" / "execution_record.json").read_text(encoding="utf-8")
    )
    papermill_parameters = json.loads(
        (run_dir / "parameters" / "papermill_parameters.json").read_text(encoding="utf-8")
    )

    for record in (execution_record, papermill_parameters):
        boundary = record["optional_dependency_boundary"]

        assert boundary["required_for_v0_1"] is False
        assert boundary["execution_enabled_by_default"] is False
        assert boundary["real_execution_allowed"] is False
        assert boundary["dependency_probe_method"] == "importlib.util.find_spec"
        assert boundary["dependencies"]["papermill"]["module"] == "papermill"
        assert isinstance(boundary["dependencies"]["papermill"]["available"], bool)
        assert boundary["dependencies"]["papermill"]["used"] is False
        assert boundary["dependencies"]["nbclient"]["module"] == "nbclient"
        assert isinstance(boundary["dependencies"]["nbclient"]["available"], bool)
        assert boundary["dependencies"]["nbclient"]["used"] is False

    result = verify_run(run_dir)

    assert result["verification_status"] == "passed"
    assert result["checks"]["optional_papermill_dependency_boundary_conservative"] == "passed"


def test_verify_fails_when_optional_dependency_boundary_allows_real_execution(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "bad_optional_dependency_demo")

    execution_record_path = run_dir / "records" / "execution_record.json"
    execution_record = json.loads(execution_record_path.read_text(encoding="utf-8"))
    execution_record["optional_dependency_boundary"]["real_execution_allowed"] = True
    execution_record["optional_dependency_boundary"]["dependencies"]["papermill"]["used"] = True
    execution_record_path.write_text(json.dumps(execution_record, indent=2), encoding="utf-8")

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["optional_papermill_dependency_boundary_conservative"] == "failed"
    assert any("real_execution_allowed must be false" in error for error in result["optional_dependency_boundary_errors"])
    assert any("dependencies.papermill.used must be false" in error for error in result["optional_dependency_boundary_errors"])


def test_papermill_execution_disabled_by_default_policy_is_recorded(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "execution_policy_demo")

    execution_record = json.loads(
        (run_dir / "records" / "execution_record.json").read_text(encoding="utf-8")
    )
    papermill_parameters = json.loads(
        (run_dir / "parameters" / "papermill_parameters.json").read_text(encoding="utf-8")
    )
    executed_notebook = json.loads(
        (run_dir / "executed" / "execution_policy_demo.executed.ipynb").read_text(encoding="utf-8")
    )

    for policy in (
        execution_record["notebook_execution_policy"],
        papermill_parameters["notebook_execution_policy"],
        executed_notebook["metadata"]["notebook_execution_policy"],
    ):
        assert policy["policy_status"] == "disabled_by_default"
        assert policy["execution_disabled_by_default"] is True
        assert policy["real_execution_permitted"] is False
        assert policy["actual_notebook_execution"] is False
        assert policy["papermill_execution_requested"] is False
        assert policy["papermill_execution_performed"] is False
        assert policy["nbclient_execution_performed"] is False
        assert policy["override_supported"] is False

    result = verify_run(run_dir)

    assert result["verification_status"] == "passed"
    assert result["checks"]["papermill_execution_disabled_by_default"] == "passed"


def test_verify_fails_when_papermill_execution_policy_claims_execution(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "bad_execution_policy_demo")

    execution_record_path = run_dir / "records" / "execution_record.json"
    execution_record = json.loads(execution_record_path.read_text(encoding="utf-8"))
    execution_record["notebook_execution_policy"]["real_execution_permitted"] = True
    execution_record["notebook_execution_policy"]["papermill_execution_performed"] = True
    execution_record_path.write_text(json.dumps(execution_record, indent=2), encoding="utf-8")

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["papermill_execution_disabled_by_default"] == "failed"
    assert any("real_execution_permitted must be false" in error for error in result["notebook_execution_policy_errors"])
    assert any("papermill_execution_performed must be false" in error for error in result["notebook_execution_policy_errors"])


def test_python_api_for_notebook_users_creates_verified_placeholder_packet(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")

    result = run_notebook_placeholder(
        workspace=workspace,
        query_job="jobs/rag_literature_demo.json",
        output_prefix="python_api_notebook_demo",
    )

    assert result["record_type"] == "notebook_placeholder_run_result"
    assert result["run_id"] == "python_api_notebook_demo"
    assert result["verified"] is True
    assert result["verification_status"] == "passed"
    assert result["checks"]["executed_notebook_stub_shape"] == "passed"
    assert result["checks"]["optional_papermill_dependency_boundary_conservative"] == "passed"
    assert result["checks"]["papermill_execution_disabled_by_default"] == "passed"
    assert result["execution_boundary"]["actual_notebook_execution"] is False
    assert result["execution_boundary"]["papermill_invoked"] is False
    assert result["execution_boundary"]["nbclient_invoked"] is False
    assert "does not claim scientific validation" in result["authority_note"]

    run_dir = Path(result["run_dir"])
    execution_record = json.loads(
        (run_dir / "records" / "execution_record.json").read_text(encoding="utf-8")
    )
    executed_notebook = json.loads(
        (run_dir / "executed" / "python_api_notebook_demo.executed.ipynb").read_text(encoding="utf-8")
    )

    assert execution_record["notebook_template"] == "notebooks/templates/literature_evidence_runner.ipynb"
    assert execution_record["executed_notebook"] == "executed/python_api_notebook_demo.executed.ipynb"
    assert execution_record["execution_backend"] == "placeholder_papermill"
    assert executed_notebook["metadata"]["actual_notebook_execution"] is False
    assert executed_notebook["metadata"]["papermill_invoked"] is False
    assert executed_notebook["metadata"]["nbclient_invoked"] is False
def test_workspace_scaffolds_notebook_template_stub_contract(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")

    template_path = workspace / "notebooks" / "templates" / "literature_evidence_runner.ipynb"
    assert template_path.exists()

    template = json.loads(template_path.read_text(encoding="utf-8"))

    assert template["nbformat"] == 4
    assert template["nbformat_minor"] == 5
    assert template["metadata"]["run_lab_template"] is True
    assert template["metadata"]["template_id"] == "literature_evidence_runner"
    assert template["metadata"]["integration_status"] == "placeholder"
    assert template["metadata"]["placeholder_for"] == "future_papermill_notebook_execution"
    assert template["metadata"]["actual_notebook_execution"] is False
    assert template["metadata"]["papermill_invoked"] is False
    assert template["metadata"]["nbclient_invoked"] is False
    assert template["metadata"]["kernelspec"]["name"] == "python3"
    assert template["metadata"]["language_info"]["name"] == "python"

    assert len(template["cells"]) == 2
    assert template["cells"][0]["cell_type"] == "markdown"
    assert template["cells"][1]["cell_type"] == "code"
    assert template["cells"][1]["execution_count"] is None
    assert template["cells"][1]["outputs"] == []
    assert "parameters" in template["cells"][1]["metadata"]["tags"]
    assert "ACTUAL_NOTEBOOK_EXECUTION = False" in "".join(template["cells"][1]["source"])

def test_verify_confirms_notebook_template_path_exists_and_is_placeholder_stub(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "template_stub_verify_demo")

    result = verify_run(run_dir)

    assert result["verification_status"] == "passed"
    assert result["checks"]["notebook_template_stub_shape"] == "passed"
    assert result["notebook_template_errors"] == []


def test_verify_fails_when_notebook_template_is_missing(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "missing_template_stub_demo")

    template_path = workspace / "notebooks" / "templates" / "literature_evidence_runner.ipynb"
    template_path.unlink()

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["notebook_template_stub_shape"] == "failed"
    assert any("notebook_template does not exist" in error for error in result["notebook_template_errors"])


def test_verify_fails_when_notebook_template_claims_execution(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "bad_template_claim_demo")

    template_path = workspace / "notebooks" / "templates" / "literature_evidence_runner.ipynb"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    template["metadata"]["actual_notebook_execution"] = True
    template["metadata"]["papermill_invoked"] = True
    template["cells"][1]["execution_count"] = 1
    template["cells"][1]["outputs"] = [{"output_type": "stream", "name": "stdout", "text": "not allowed"}]
    template_path.write_text(json.dumps(template, indent=2), encoding="utf-8")

    result = verify_run(run_dir)

    assert result["verification_status"] == "failed"
    assert result["checks"]["notebook_template_stub_shape"] == "failed"
    assert any("actual_notebook_execution must be false" in error for error in result["notebook_template_errors"])
    assert any("papermill_invoked must be false" in error for error in result["notebook_template_errors"])
    assert any("execution_count must be null" in error for error in result["notebook_template_errors"])
    assert any("outputs must be empty" in error for error in result["notebook_template_errors"])

