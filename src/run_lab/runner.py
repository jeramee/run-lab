from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from importlib.util import find_spec
import html

from .constants import AUTHORITY_FLAGS, PLACEHOLDER_AUTHORITY_FLAGS
from .io import read_json, write_json, sha256_file


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _placeholder_fields(placeholder_for: str) -> dict:
    return {
        "integration_status": "placeholder",
        "placeholder_for": placeholder_for,
        "placeholder_authority_flags": dict(PLACEHOLDER_AUTHORITY_FLAGS),
    }
    
    
def _optional_dependency_boundary() -> dict:
    return {
        "required_for_v0_1": False,
        "execution_enabled_by_default": False,
        "real_execution_allowed": False,
        "dependency_probe_method": "importlib.util.find_spec",
        "dependencies": {
            "papermill": {
                "module": "papermill",
                "available": find_spec("papermill") is not None,
                "used": False,
            },
            "nbclient": {
                "module": "nbclient",
                "available": find_spec("nbclient") is not None,
                "used": False,
            },
        },
        "authority_note": "Optional dependency availability is recorded only; RunLab v0.1 does not execute notebooks.",
    }    
    

def run_demo(workspace: str | Path, query_job: str | Path, output_prefix: str = "rag_literature_demo", render: str = "html") -> Path:
    root = Path(workspace)
    job_path = Path(query_job)
    if not job_path.is_absolute():
        job_path = root / job_path
    job = read_json(job_path)
    run_dir = root / "runs" / output_prefix
    if run_dir.exists():
        raise FileExistsError(f"Run packet already exists and will not be overwritten: {run_dir}")
    for sub in ("inputs", "parameters", "executed", "records", "context", "reports", "logs"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)

    index_path = root / job.get("index_ref", "indexes/local_demo_index.json")
    index = read_json(index_path)
    max_results = int(job.get("max_results", 3))
    selected = index.get("records", [])[:max_results]
    created = _now()

    write_json(run_dir / "inputs" / "query_job.json", {
        "record_type": "query_job",
        "run_id": output_prefix,
        "job_id": job.get("job_id", job_path.stem),
        "query": job.get("query"),
        "index_ref": job.get("index_ref", "indexes/local_demo_index.json"),
        "citation_mode": job.get("citation_mode", "locator_only"),
        "max_results": max_results,
        "source_job_path": job_path.relative_to(root).as_posix() if job_path.is_relative_to(root) else str(job_path),
        "authority_flags": dict(AUTHORITY_FLAGS),
        **_placeholder_fields("future_query_job_contract"),
    })

    write_json(run_dir / "inputs" / "index_reference.json", {
        "record_type": "index_reference",
        "run_id": output_prefix,
        "index_id": index.get("index_id", index_path.stem),
        "backend": index.get("backend", "static_local_demo"),
        "source_index_path": index_path.relative_to(root).as_posix() if index_path.is_relative_to(root) else str(index_path),
        "record_count": len(index.get("records", [])),
        "selected_count": len(selected),
        "records": selected,
        "authority_flags": dict(AUTHORITY_FLAGS),
        **_placeholder_fields("future_txtai_index_reference"),
    })

    notebook_template = job.get("notebook_template", "notebooks/templates/literature_evidence_runner.ipynb")
    executed_notebook = f"executed/{output_prefix}.executed.ipynb"
    optional_dependency_boundary = _optional_dependency_boundary()

    write_json(run_dir / "parameters" / "papermill_parameters.json", {
        "record_type": "papermill_parameters",
        "run_id": output_prefix,
        "execution_mode": "placeholder_no_papermill",
        "execution_backend": "placeholder_papermill",
        "optional_dependency_boundary": optional_dependency_boundary,        
        "notebook_template": notebook_template,
        "executed_notebook": executed_notebook,
        "query": job.get("query"),
        "authority_flags": dict(AUTHORITY_FLAGS),
        **_placeholder_fields("future_papermill_notebook_execution"),
    })

    write_json(run_dir / "records" / "retrieval_record.json", {
        "record_type": "retrieval_record",
        "run_id": output_prefix,
        "backend": "static_local_demo",
        "query": job.get("query"),
        "results": selected,
        "authority_flags": dict(AUTHORITY_FLAGS),
        **_placeholder_fields("future_txtai_retrieval"),
        "authority_note": "Retrieval evidence is not validation."
    })

    write_json(run_dir / "records" / "source_citation_record.json", {
        "record_type": "source_citation_record",
        "run_id": output_prefix,
        "citation_status": "locator_records_present",
        "citations": [
            {"citation_id": f"citation_{i:03d}", "source_id": r.get("source_id"), "title": r.get("title"), "support_status": "not_evaluated"}
            for i, r in enumerate(selected, start=1)
        ],
        "authority_flags": dict(AUTHORITY_FLAGS),
        **_placeholder_fields("future_source_citation_validation"),
    })

    context_markdown = "# Context Pack\n\n" + "\n\n".join(f"## {r.get('title')}\n{r.get('text')}" for r in selected)
    context_markdown += "\n\n## Authority Boundary\nThis context supports inspection only. It does not prove scientific correctness.\n"
    context_path = run_dir / "context" / "context_pack.md"
    context_path.write_text(context_markdown, encoding="utf-8")

    write_json(run_dir / "records" / "context_pack.json", {
        "record_type": "context_pack",
        "run_id": output_prefix,
        "context_file": "context/context_pack.md",
        "source_count": len(selected),
        "authority_flags": dict(AUTHORITY_FLAGS),
        **_placeholder_fields("future_context_pack_builder"),
        "authority_note": "Context supports inspection only and does not prove correctness.",
    })

    executed = run_dir / executed_notebook
    write_json(executed, _build_placeholder_notebook_stub(
        run_id=output_prefix,
        query=job.get("query"),
        notebook_template=notebook_template,
    ))

    write_json(run_dir / "records" / "execution_record.json", {
        "record_type": "execution_record",
        "run_id": output_prefix,
        "execution_status": "placeholder_executed",
        "execution_backend": "placeholder_papermill",
        "optional_dependency_boundary": optional_dependency_boundary,
        "notebook_template": notebook_template,
        "executed_notebook": executed_notebook,
        "authority_flags": dict(AUTHORITY_FLAGS),
        **_placeholder_fields("future_papermill_notebook_execution"),
    })

    write_json(run_dir / "records" / "environment_report.json", {
        "record_type": "environment_report",
        "run_id": output_prefix,
        "captured_at": created,
        "environment_status": "partial_static_capture",
        "raw_environment_dumped": False,
        "authority_flags": dict(AUTHORITY_FLAGS),
        **_placeholder_fields("future_environment_capture"),
    })

    markdown = f"# {output_prefix}\n\nQuery: {job.get('query')}\n\nThis is a demo report. Evidence is not proof.\n"
    (run_dir / "reports" / "report.md").write_text(markdown, encoding="utf-8")
    # Backward-compatible report alias during v0.1 scaffold hardening.
    (run_dir / "reports" / "rendered_report.md").write_text(markdown, encoding="utf-8")
    if render == "html":
        html_report = f"<h1>{html.escape(output_prefix)}</h1><p>Evidence is not proof.</p>"
        (run_dir / "reports" / "report.html").write_text(html_report, encoding="utf-8")
        # Backward-compatible report alias during v0.1 scaffold hardening.
        (run_dir / "reports" / "rendered_report.html").write_text(html_report, encoding="utf-8")

    _write_manifests(run_dir, output_prefix, created)
    return run_dir


def _build_placeholder_notebook_stub(run_id: str, query: str | None, notebook_template: str) -> dict:
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {
                    "run_lab_cell_role": "evidence_boundary_notice",
                },
                "source": [
                    "# RunLab placeholder notebook stub\n",
                    "\n",
                    "This notebook-shaped artifact was generated for evidence-packet inspection only.\n",
                    "It was not executed by Papermill, nbclient, Jupyter Notebook, or JupyterLab.\n",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {
                    "run_lab_cell_role": "placeholder_parameters",
                    "integration_status": "placeholder",
                    "placeholder_for": "future_papermill_notebook_execution",
                },
                "outputs": [],
                "source": [
                    "# Placeholder parameters for future Papermill execution\n",
                    f"RUN_ID = {run_id!r}\n",
                    f"QUERY = {query!r}\n",
                    f"NOTEBOOK_TEMPLATE = {notebook_template!r}\n",
                    "ACTUAL_NOTEBOOK_EXECUTION = False\n",
                ],
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
            "run_lab_execution": "placeholder",
            "run_id": run_id,
            "notebook_template": notebook_template,
            "execution_backend": "placeholder_papermill",
            "integration_status": "placeholder",
            "placeholder_for": "future_papermill_notebook_execution",
            "actual_notebook_execution": False,
            "papermill_invoked": False,
            "nbclient_invoked": False,
            "optional_dependency_boundary": _optional_dependency_boundary(),
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _write_manifests(run_dir: Path, run_id: str, created: str) -> None:
    replay_manifest_path = run_dir / "records" / "replay_manifest.json"
    artifact_manifest_path = run_dir / "records" / "artifact_manifest.json"

    replay_artifacts = [
        "inputs/query_job.json",
        "inputs/index_reference.json",
        "parameters/papermill_parameters.json",
        "records/retrieval_record.json",
        "records/source_citation_record.json",
        "records/context_pack.json",
        "context/context_pack.md",
        "records/execution_record.json",
        "records/environment_report.json",
        f"executed/{run_id}.executed.ipynb",
        "reports/report.md",
    ]
    html_report = run_dir / "reports" / "report.html"
    if html_report.exists():
        replay_artifacts.append("reports/report.html")

    write_json(replay_manifest_path, {
        "record_type": "replay_manifest",
        "run_id": run_id,
        "created_at": created,
        "replay_status": "not_run",
        "replay_scope": "static_demo_run",
        "replay_artifacts": replay_artifacts,
        "replay_command": [
            "run-lab",
            "run",
            "--workspace",
            ".",
            "--query-job",
            "jobs/rag_literature_demo.json",
            "--output-prefix",
            run_id,
        ],
        "authority_flags": dict(AUTHORITY_FLAGS),
        **_placeholder_fields("future_replay_execution"),
        "limitations": [
            "Replay metadata records the intended local run shape only.",
            "No Papermill execution in this rough scaffold.",
            "No scientific validation.",
        ],
    })

    artifacts = []
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file()):
        if path == artifact_manifest_path:
            continue
        rel = path.relative_to(run_dir).as_posix()
        artifacts.append({"path": rel, "hash": {"algorithm": "sha256", "value": sha256_file(path)}})

    artifacts.append({
        "path": artifact_manifest_path.relative_to(run_dir).as_posix(),
        "hash_status": "not_applicable_self_referential_manifest",
        "authority_note": "The manifest lists itself, but does not hash itself because that would be self-referential.",
    })

    write_json(artifact_manifest_path, {
        "record_type": "artifact_manifest",
        "run_id": run_id,
        "created_at": created,
        "artifacts": artifacts,
        "authority_flags": dict(AUTHORITY_FLAGS),
    })
