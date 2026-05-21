from __future__ import annotations
from pathlib import Path
from .io import read_json


def inspect_replay_manifest(path: str | Path) -> dict:
    manifest = read_json(path)
    return {
        "record_type": "replay_inspection_report",
        "run_id": manifest.get("run_id"),
        "replay_status": manifest.get("replay_status"),
        "replay_scope": manifest.get("replay_scope"),
        "replay_artifacts": manifest.get("replay_artifacts", []),
        "replay_command": manifest.get("replay_command", []),
        "authority_flags": manifest.get("authority_flags", {}),
        "limitations": manifest.get("limitations", []),
        "authority_note": "Replay metadata is not replay success.",
    }
