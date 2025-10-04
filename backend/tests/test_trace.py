from unittest.mock import MagicMock

import pytest

from app.api import trace as trace_module


class DummyRecord(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class DummyNode(dict):
    def __init__(self, address, labels=None, **properties):
        super().__init__(address=address, **properties)
        self.labels = set(labels or ['Address'])

    def get(self, key, default=None):
        return super().get(key, default)


class DummyRelationship(dict):
    def __init__(self, start_node, end_node, **properties):
        super().__init__(**properties)
        self.start_node = start_node
        self.end_node = end_node
        self.type = 'SENT'

    def get(self, key, default=None):
        return super().get(key, default)


class DummyPath:
    def __init__(self, nodes, relationships):
        self.nodes = nodes
        self.relationships = relationships


class DummySession:
    def __init__(self, records):
        self._records = records

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def run(self, *_args, **_kwargs):
        return self._records


class DummyDriver:
    def __init__(self, records):
        self._records = records

    def session(self):
        return DummySession(self._records)


@pytest.fixture()
def tracedriver(monkeypatch):
    sender_addr = '0x' + 'a' * 40
    receiver_addr = '0x' + 'b' * 40
    sender = DummyNode(sender_addr, cluster_id='cluster-1')
    receiver = DummyNode(receiver_addr, cluster_id='cluster-2', risk_score=0.99)
    relationship = DummyRelationship(
        sender,
        receiver,
        hash='0xhash',
        value_wei=123,
        timestamp=1680000000,
        block_number=123456,
    )
    path = DummyPath([sender, receiver], [relationship])
    records = [DummyRecord(path=path)]

    driver = DummyDriver(records)
    monkeypatch.setattr(trace_module, 'get_driver', lambda: driver)

    return driver, sender_addr, receiver_addr


def test_trace_returns_graph(client, tracedriver):
    _driver, sender_addr, receiver_addr = tracedriver
    payload = {"from": sender_addr, "to": receiver_addr, "max_hops": 3}
    response = client.post('/trace', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['metadata']['edge_count'] == 1
    assert len(data['nodes']) == 2
    assert any(node['address'] == sender_addr for node in data['nodes'])
