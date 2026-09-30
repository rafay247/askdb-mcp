from __future__ import annotations

from pathlib import Path

import pytest

from askdb_mcp.demo_db import create_demo_database


@pytest.fixture
def demo_db(tmp_path: Path) -> Path:
    path = tmp_path / "demo.sqlite"
    create_demo_database(path)
    return path
