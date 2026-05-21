AUTHORITY_FLAGS = {
    "correctness_proven": False,
    "repo_mutated": False,
    "state_promoted": False,
    "source_control_touched": False,
}

PLACEHOLDER_AUTHORITY_FLAGS = {
    "mechanical_verification_only": True,
    "scientific_validation": False,
    "promotion_authority": False,
}

ALLOWED_VERIFICATION_STATUSES = {
    "passed",
    "failed",
    "passed_with_warnings",
    "not_run",
}

WORKSPACE_DIRS = [
    "jobs",
    "indexes",
    "notebooks/templates",
    "runs",
    "reports",
]
