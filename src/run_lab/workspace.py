from __future__ import annotations
from pathlib import Path
from .constants import AUTHORITY_FLAGS, PLACEHOLDER_AUTHORITY_FLAGS, WORKSPACE_DIRS
from .io import write_json


def _placeholder_fields(placeholder_for: str) -> dict:
    return {
        "integration_status": "placeholder",
        "placeholder_for": placeholder_for,
        "placeholder_authority_flags": dict(PLACEHOLDER_AUTHORITY_FLAGS),
    }


def init_workspace(path: str | Path) -> Path:
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    for rel in WORKSPACE_DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)
    write_json(root / "run_lab.yml.json", {
        "record_type": "run_lab_workspace_config",
        "workspace_type": "run_lab",
        "version": "0.1",
        "authority_flags": dict(AUTHORITY_FLAGS),
        "authority_note": "RunLab produces evidence, not scientific proof."
    })
    demo_job = root / "jobs" / "rag_literature_demo.json"
    if not demo_job.exists():
        write_json(demo_job, {
            "record_type": "query_job",
            "job_id": "rag_literature_demo",
            "query": "demo literature evidence run",
            "index_ref": "indexes/local_demo_index.json",
            "citation_mode": "locator_only",
            "max_results": 3,
            "authority_flags": dict(AUTHORITY_FLAGS),
            **_placeholder_fields("future_query_job_contract"),
        })
    demo_index = root / "indexes" / "local_demo_index.json"
    if not demo_index.exists():
        write_json(demo_index, {
            "record_type": "index_reference",
            "index_id": "local_demo_index",
            "backend": "static_local_demo",
            "authority_flags": dict(AUTHORITY_FLAGS),
            **_placeholder_fields("future_txtai_index_reference"),
            "records": [
                {"source_id": "source_001", "title": "Demo Source", "text": "RunLab demo source text."}
            ],
        })
    template = root / "notebooks" / "templates" / "literature_evidence_runner.ipynb"
    if not template.exists():
        write_json(template, {
            "cells": [],
            "metadata": {
                "run_lab_template": True,
                "integration_status": "placeholder",
                "placeholder_for": "future_notebook_template_execution",
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        })
    return root


def inspect_workspace(path: str | Path) -> dict:
    root = Path(path)
    return {
        "record_type": "workspace_inspection_report",
        "workspace": str(root),
        "exists": root.exists(),
        "jobs": sorted(p.name for p in (root / "jobs").glob("*.json")) if (root / "jobs").exists() else [],
        "runs": sorted(p.name for p in (root / "runs").iterdir()) if (root / "runs").exists() else [],
        "authority_flags": dict(AUTHORITY_FLAGS),
        "authority_note": "RunLab workspace inspection reports local workspace shape only, not validation, certification, approval, promotion, or scientific correctness.",
    }
