def test_health_is_public_and_has_no_secrets(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
    assert 'token' not in response.text.lower()

def test_version_identifies_deterministic_authority(client):
    response = client.get('/version')
    assert response.status_code == 200
    assert response.json()['engine_version'] == '0.3.0'

def test_missing_service_credentials_fail_closed(client):
    response = client.post('/v1/theory/interval', headers={'Authorization': ''}, json={'inputs': {'first': 'C4', 'second': 'Eb4'}})
    assert response.status_code == 401

def test_mixed_region_service_call_fails_closed(client):
    response = client.post('/v1/theory/interval', headers={'X-Home-Region': 'cn'}, json={'inputs': {'first': 'C4', 'second': 'Eb4'}})
    assert response.status_code == 403

def test_missing_region_configuration_fails_closed(client, monkeypatch):
    monkeypatch.delenv('THEORY_HOME_REGION')
    assert client.post('/v1/theory/interval', json={'inputs': {'first': 'C4', 'second': 'Eb4'}}).status_code == 503
