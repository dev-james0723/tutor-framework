import pytest
from fastapi.testclient import TestClient
from theory_api.main import app

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('THEORY_API_TOKEN', 'local-test-only-token')
    monkeypatch.setenv('THEORY_HOME_REGION', 'global')
    return TestClient(app, headers={'Authorization': 'Bearer local-test-only-token', 'X-Home-Region': 'global'})
