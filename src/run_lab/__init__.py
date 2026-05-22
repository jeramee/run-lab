"""RunLab v0.1 public API.

The public API is intentionally conservative. It creates and verifies local
evidence packets, but it does not execute Papermill, nbclient, Jupyter Notebook,
or JupyterLab notebooks in v0.1.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .workspace import init_workspace, inspect_workspace
from .runner import run_demo
from .verify import verify_run


def run_notebook_placeholder(
    workspace: str | Path,
    query_job: str | Path = "jobs/rag_literature_demo.json",
    output_prefix: str = "rag_literature_demo",
    render: str = "html",
    verify: bool = True,
) -> dict[str, Any]:
    """Create a placeholder notebook evidence packet for notebook users.

    This is a notebook-friendly wrapper around the v0.1 local packet runner.
    It records notebook-template and executed-notebook placeholder artifacts, but
    it does not perform real notebook execution.

    Returns a small dictionary that is easy to inspect in Jupyter cells.
    """
    run_dir = run_demo(
        workspace=workspace,
        query_job=query_job,
        output_prefix=output_prefix,
        render=render,
    )

    verification_report = verify_run(run_dir) if verify else None

    return {
        "record_type": "notebook_placeholder_run_result",
        "run_id": output_prefix,
        "run_dir": str(run_dir),
        "query_job": str(query_job),
        "render": render,
        "verified": verification_report is not None,
        "verification_status": (
            verification_report.get("verification_status")
            if verification_report is not None
            else "not_run"
        ),
        "checks": (
            verification_report.get("checks", {})
            if verification_report is not None
            else {}
        ),
        "execution_boundary": {
            "actual_notebook_execution": False,
            "papermill_invoked": False,
            "nbclient_invoked": False,
            "jupyter_notebook_invoked": False,
            "jupyterlab_invoked": False,
        },
        "authority_note": (
            "run_notebook_placeholder creates a local evidence packet only; "
            "it does not claim scientific validation or real notebook execution."
        ),
    }


__all__ = [
    "init_workspace",
    "inspect_workspace",
    "run_demo",
    "run_notebook_placeholder",
    "verify_run",
]

__version__ = "0.1.0a0"
