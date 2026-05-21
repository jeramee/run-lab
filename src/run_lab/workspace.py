from __future__ import annotations
from pathlib import Path
from .constants import WORKSPACE_DIRS
from .io import write_json

def init_workspace(path: str | Path) -> Path:
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    for rel in WORKSPACE_DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)
    write_json(root / "run_lab.yml.json", {
        "workspace_type": "run_lab",
        "version": "0.1",
        "authority_note": "RunLab produces evidence, not scientific proof."
    })
    demo_job = root / "jobs" / "rag_literature_demo.json"
    if not demo_job.exists():
        write_json(demo_job, {
            "job_id": "rag_literature_demo",
            "query": "demo literature evidence run",
            "index_ref": "indexes/local_demo_index.json",
            "citation_mode": "locator_only",
            "max_results": 3,
        })
    demo_index = root / "indexes" / "local_demo_index.json"
    if not demo_index.exists():
        write_json(demo_index, {
            "index_id": "local_demo_index",
            "backend": "static_local_demo",
            "records": [
                {"source_id": "source_001", "title": "Demo Source", "text": "RunLab demo source text."}
            ],
        })
    template = root / "notebooks" / "templates" / "literature_evidence_runner.ipynb"
    if not template.exists():
        write_json(template, {
            "cells": [],
            "metadata": {"run_lab_template": True},
            "nbformat": 4,
            "nbformat_minor": 5,
        })
    return root

def inspect_workspace(path: str | Path) -> dict:
    root = Path(path)
    return {
        "workspace": str(root),
        "exists": root.exists(),
        "jobs": sorted(p.name for p in (root / "jobs").glob("*.json")) if (root / "jobs").exists() else [],
        "runs": sorted(p.name for p in (root / "runs").iterdir()) if (root / "runs").exists() else [],
    }
