import pytest

from app.ingest import etherscan_ingest as ingest_module


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("ETHERSCAN_API_KEY", "test-key")


def test_fetch_transactions_handles_no_results(monkeypatch):
    payload = {
        "status": "0",
        "message": "No transactions found",
        "result": "No transactions found",
    }

    monkeypatch.setattr(ingest_module.requests, "get", lambda *_, **__: DummyResponse(payload))

    result = ingest_module._fetch_transactions("0x1111111111111111111111111111111111111111")
    assert result == []


def test_fetch_transactions_invalid_address(monkeypatch):
    payload = {
        "status": "0",
        "message": "NOTOK",
        "result": "Error! Invalid address format",
    }

    monkeypatch.setattr(ingest_module.requests, "get", lambda *_, **__: DummyResponse(payload))

    with pytest.raises(ValueError):
        ingest_module._fetch_transactions("0xinvalid")


def test_fetch_transactions_rate_limit(monkeypatch):
    payload = {
        "status": "0",
        "message": "NOTOK",
        "result": "Max rate limit reached",
    }

    monkeypatch.setattr(ingest_module.requests, "get", lambda *_, **__: DummyResponse(payload))

    with pytest.raises(RuntimeError) as excinfo:
        ingest_module._fetch_transactions("0x1111111111111111111111111111111111111111")

    assert "rate limit" in str(excinfo.value).lower()


def test_fetch_transactions_unexpected_payload(monkeypatch):
    payload = {
        "status": "1",
        "message": "OK",
        "result": "unexpected string",
    }

    monkeypatch.setattr(ingest_module.requests, "get", lambda *_, **__: DummyResponse(payload))

    with pytest.raises(RuntimeError) as excinfo:
        ingest_module._fetch_transactions("0x1111111111111111111111111111111111111111")

    assert "unexpected" in str(excinfo.value).lower()


def test_ingest_address_transactions_persists(monkeypatch):
    transaction = ingest_module.TransactionRecord(
        hash="0xabc",
        block_number=1,
        timestamp=1234567890,
        from_address="0x1111111111111111111111111111111111111111",
        to_address="0x2222222222222222222222222222222222222222",
        value_wei=10**18,
        gas=21000,
        gas_price_wei=100,
    )

    monkeypatch.setattr(ingest_module, "_fetch_transactions", lambda _address: [transaction])

    recorded = {}

    class DummySession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def run(self, query, transactions):
            recorded["query"] = query
            recorded["transactions"] = transactions

    class DummyDriver:
        def session(self):
            return DummySession()

    monkeypatch.setattr(ingest_module, "get_driver", lambda: DummyDriver())

    result = ingest_module.ingest_address_transactions(transaction.from_address)

    assert recorded["transactions"][0]["hash"] == "0xabc"
    assert result["fetched_count"] == 1
    assert result["ingested_count"] == 1
    assert pytest.approx(result["total_value_eth"], rel=1e-9) == 1.0
