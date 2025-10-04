import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure the backend app is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402  pylint: disable=wrong-import-position


@pytest.fixture()
def client():
    return TestClient(app)
