from __future__ import annotations
from pathlib import Path
from .io import read_json

def inspect_replay_manifest(path: str | Path) -> dict:
    manifest = read_json(path)
    return {
        "replay_status": manifest.get("replay_status"),
        "replay_scope": manifest.get("replay_scope"),
        "limitations": manifest.get("limitations", []),
        "authority_note": "Replay metadata is not replay success.",
    }
