def test_buscar_por_cedula_no_encontrada(client):
    response = client.get("/busqueda/cedula/V99999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "No se encontró un ciudadano con esa cédula"
