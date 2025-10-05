from pathlib import Path

import pytest

from app.ingest import sample_loader


def test_load_sample_transactions_uses_driver(monkeypatch):
    sample_path = Path(__file__).resolve().parents[2] / "data" / "sample_txns.json"
    executed = {}

    class DummySession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def run(self, query, transactions):
            executed["query"] = query
            executed["transactions"] = transactions

    class DummyDriver:
        def session(self):
            executed["session"] = True
            return DummySession()

    monkeypatch.setattr(sample_loader, "get_driver", lambda: DummyDriver())

    result = sample_loader.load_sample_transactions(str(sample_path))

    assert result["transaction_count"] == 3
    assert result["unique_addresses"] == 3
    assert pytest.approx(result["total_value_eth"], rel=1e-6) == 4.0
    assert executed["session"] is True
    assert executed["query"].strip().startswith("UNWIND")
    assert len(executed["transactions"]) == 3


def test_ingest_sample_endpoint_success(client, monkeypatch):
    from app import main as main_module

    sample_response = {
        "transaction_count": 3,
        "unique_addresses": 3,
        "total_value_eth": 4.0,
        "source": "sample",
    }

    async def fake_run_in_threadpool(func, *args, **kwargs):
        assert func is main_module.load_sample_transactions
        return sample_response

    monkeypatch.setattr(main_module, "run_in_threadpool", fake_run_in_threadpool)

    response = client.post("/ingest/sample")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == sample_response
    assert payload["message"] == "Sample dataset ingested into Neo4j"
