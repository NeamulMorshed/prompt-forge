from app.db.base import Base
from app.db import models  # noqa: F401 — registers tables on Base.metadata


def test_all_core_tables_registered():
    expected = {
        "users",
        "workspaces",
        "context_profiles",
        "domain_packs",
        "sessions",
        "prompts",
        "prompt_versions",
        "outcome_ratings",
        "patterns",
    }
    assert expected <= set(Base.metadata.tables.keys())
