"""Mock National HR / Civil Registry lookup.

In production this would be an authenticated call to the government HR
service. Here we read a static JSON snapshot at module import.
"""

import json
from functools import lru_cache
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "mock_data" / "hr_registry.json"


@lru_cache(maxsize=1)
def _load_registry() -> dict:
    with REGISTRY_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def get_auditor(auditor_id: str) -> dict | None:
    return _load_registry().get(auditor_id)


def reload_registry() -> None:
    """Tests can call this to reset the lru_cache after monkeypatching."""
    _load_registry.cache_clear()
