from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import html
import shutil

from .constants import AUTHORITY_FLAGS
from .io import read_json, write_json, sha256_file

def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def run_demo(workspace: str | Path, query_job: str | Path, output_prefix: str = "rag_literature_demo", render: str = "html") -> Path:
    root = Path(workspace)
    job_path = Path(query_job)
    if not job_path.is_absolute():
        job_path = root / job_path
    job = read_json(job_path)
    run_dir = root / "runs" / output_prefix
    for sub in ("inputs", "parameters", "executed", "records", "context", "reports", "logs"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)

    index_path = root / job.get("index_ref", "indexes/local_demo_index.json")
    index = read_json(index_path)
    selected = index.get("records", [])[: job.get("max_results", 3)]
    created = _now()

    shutil.copy2(job_path, run_dir / "inputs" / "query_job.json")
    shutil.copy2(index_path, run_dir / "inputs" / "index_reference.json")
    write_json(run_dir / "parameters" / "papermill_parameters.json", {
        "execution_mode": "placeholder_no_papermill",
        "query": job.get("query"),
    })

    write_json(run_dir / "records" / "retrieval_record.json", {
        "record_type": "retrieval_record",
        "run_id": output_prefix,
        "backend": "static_local_demo",
        "query": job.get("query"),
        "results": selected,
        "authority_note": "Retrieval evidence is not validation."
    })
    write_json(run_dir / "records" / "source_citations.json", {
        "record_type": "source_citations",
        "run_id": output_prefix,
        "citation_status": "citation_records_present",
        "citations": [
            {"citation_id": f"citation_{i:03d}", "source_id": r.get("source_id"), "title": r.get("title"), "support_status": "not_evaluated"}
            for i, r in enumerate(selected, start=1)
        ],
    })
    context = "# Context Pack\n\n" + "\n\n".join(f"## {r.get('title')}\n{r.get('text')}" for r in selected)
    context += "\n\n## Authority Boundary\nThis context supports inspection only. It does not prove scientific correctness.\n"
    (run_dir / "context" / "context_pack.md").write_text(context, encoding="utf-8")

    executed = run_dir / "executed" / f"{output_prefix}.executed.ipynb"
    write_json(executed, {"cells": [], "metadata": {"run_lab_execution": "placeholder"}, "nbformat": 4, "nbformat_minor": 5})

    write_json(run_dir / "records" / "notebook_run_record.json", {
        "record_type": "notebook_run_record",
        "run_id": output_prefix,
        "execution_status": "placeholder_executed",
        "execution_backend": "static_placeholder_no_papermill",
        "executed_notebook": str(executed.relative_to(run_dir)),
        "authority_flags": dict(AUTHORITY_FLAGS),
    })
    write_json(run_dir / "records" / "environment_report.json", {
        "record_type": "environment_report",
        "run_id": output_prefix,
        "captured_at": created,
        "environment_status": "partial_static_capture",
        "raw_environment_dumped": False,
    })

    markdown = f"# {output_prefix}\n\nQuery: {job.get('query')}\n\nThis is a demo report. Evidence is not proof.\n"
    (run_dir / "reports" / "rendered_report.md").write_text(markdown, encoding="utf-8")
    if render == "html":
        (run_dir / "reports" / "rendered_report.html").write_text(f"<h1>{html.escape(output_prefix)}</h1><p>Evidence is not proof.</p>", encoding="utf-8")

    _write_manifests(run_dir, output_prefix, created)
    return run_dir

def _write_manifests(run_dir: Path, run_id: str, created: str) -> None:
    replay_manifest_path = run_dir / "records" / "replay_manifest.json"
    artifact_manifest_path = run_dir / "records" / "artifact_manifest.json"

    replay_artifacts = [
        "inputs/query_job.json",
        "inputs/index_reference.json",
        "parameters/papermill_parameters.json",
        "records/retrieval_record.json",
        "records/source_citations.json",
        "context/context_pack.md",
        "records/notebook_run_record.json",
        "records/environment_report.json",
        f"executed/{run_id}.executed.ipynb",
        "reports/rendered_report.md",
    ]
    html_report = run_dir / "reports" / "rendered_report.html"
    if html_report.exists():
        replay_artifacts.append("reports/rendered_report.html")

    write_json(replay_manifest_path, {
        "record_type": "replay_manifest",
        "run_id": run_id,
        "created_at": created,
        "replay_status": "replay_not_attempted",
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
