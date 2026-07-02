def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_listar_ciudadanos_vacio(client):
    response = client.get("/ciudadanos/")
    assert response.status_code == 200
    assert response.json() == []
