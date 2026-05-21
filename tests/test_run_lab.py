from pathlib import Path
from run_lab.workspace import init_workspace, inspect_workspace
from run_lab.runner import run_demo
from run_lab.verify import verify_run

def test_run_lab_workspace_run_verify(tmp_path):
    workspace = init_workspace(tmp_path / "workspace")
    state = inspect_workspace(workspace)
    assert state["exists"]
    run_dir = run_demo(workspace, "jobs/rag_literature_demo.json", "demo")
    result = verify_run(run_dir)
    assert result["verification_status"] == "passed_mechanical_checks"
    assert (run_dir / "reports" / "rendered_report.md").exists()
    assert not (run_dir / "records" / "lab_run_record.json").exists()
