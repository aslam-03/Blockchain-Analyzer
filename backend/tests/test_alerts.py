import pytest

from app.api import alerts as alerts_module


@pytest.fixture(autouse=True)
def mock_alerts(monkeypatch):
    sample_alerts = [
        {
            'address': '0xalert1',
            'cluster_id': 'cluster-1',
            'risk_score': 0.97,
            'is_anomaly': True,
            'is_sanctioned': False,
            'severity': 'HIGH',
        }
    ]

    monkeypatch.setattr(alerts_module, 'fetch_alerts', lambda limit=25: (sample_alerts, len(sample_alerts)))


def test_alerts_endpoint(client):
    response = client.get('/alerts')
    assert response.status_code == 200
    payload = response.json()
    assert payload['alerts'][0]['address'] == '0xalert1'
    assert payload['alerts'][0]['severity'] == 'HIGH'
    assert payload['total'] == 1
