from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from benchproof.api import main as api_main


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """API client bound to a fresh temporary SQLite file with no provider configured."""
    monkeypatch.setattr(api_main.settings, "database_path", str(tmp_path / "test.db"))
    monkeypatch.setattr(api_main.settings, "nebius_api_key", "")
    monkeypatch.setattr(api_main.settings, "nebius_model_id", "")
    with TestClient(api_main.app) as c:
        yield c
