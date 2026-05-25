# SRS v1.1 Dispatcher Dev Smoke for RunLab

## Goal

Use Agent Dispatch to inspect and plan a small, safe development step for the RunLab reproducible research workbench.

## Target repository

/home/jeramee/.openclaw/workspace/control-repos/run-lab

## Current baseline

The repo is green at 34 local pytest tests.

## Requested dispatcher behavior

Create a Tier 1 planning/source packet only. Do not mutate source files yet.

## Constraints

- Treat LocalGPT/txtai retrieval as context evidence only.
- Do not treat retrieval as routing authority, correctness validation, mutation permission, or promotion truth.
- Do not run blindwrite from this SRS.
- Do not push or settle source control.
- Preserve repo-local dispatcher evidence under .dispatch/.

## Desired next planning target

Inspect RunLab’s current CLI, verification, replay, and packet/report contract, then propose the smallest useful next development step that connects RunLab more cleanly to EvidenceAI Core and TraceLab evidence bundles.

## Validation expectation

Before any future implementation, the repo must remain green with:

PYTHONPATH=src python3 -m pytest -q
