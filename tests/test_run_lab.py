from pathlib import Path
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
    assert result["verification_status"] == "pass"
    assert (run_dir / "reports" / "rendered_report.md").exists()

    verification_report = run_dir / "records" / "verification_report.json"
    assert verification_report.exists()

    artifact_manifest = (run_dir / "records" / "artifact_manifest.json").read_text(encoding="utf-8")
    assert "records/replay_manifest.json" in artifact_manifest
    assert "records/artifact_manifest.json" in artifact_manifest
    assert "records/verification_report.json" in artifact_manifest

    replay_report = inspect_replay_manifest(run_dir / "records" / "replay_manifest.json")
    assert replay_report["record_type"] == "replay_inspection_report"
    assert replay_report["run_id"] == "demo"
    assert "inputs/query_job.json" in replay_report["replay_artifacts"]
    assert "reports/rendered_report.md" in replay_report["replay_artifacts"]
    assert replay_report["authority_flags"]["correctness_proven"] is False

    assert not (run_dir / "records" / "lab_run_record.json").exists()
