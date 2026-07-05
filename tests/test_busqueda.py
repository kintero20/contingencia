import pytest


pytestmark = pytest.mark.asyncio


async def test_buscar_por_cedula_no_encontrada(client):
    response = await client.get("/busqueda/cedula/V99999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "No se encontró un ciudadano con esa cédula"


async def test_buscar_por_cedula_encontrada(client):
    await client.post("/ciudadanos/", data={
        "cedula": "V12345678",
        "nombre": "Ana",
        "apellido": "Lopez",
    })
    response = await client.get("/busqueda/cedula/V12345678")
    assert response.status_code == 200
    data = response.json()
    assert data["cedula"] == "V12345678"
    assert data["nombre"] == "Ana"


async def test_busqueda_facial_sin_rostro(client, sample_image):
    response = await client.post(
        "/busqueda/facial?limite=5&umbral=0.5",
        files={"foto": ("face.jpg", sample_image, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "resultados" in data
    assert "total" in data
    assert data["total"] == 0


async def test_busqueda_facial_sin_foto(client):
    response = await client.post("/busqueda/facial")
    assert response.status_code == 422


async def test_busqueda_facial_foto_vacia(client):
    response = await client.post(
        "/busqueda/facial",
        files={"foto": ("empty.jpg", b"", "image/jpeg")},
    )
    assert response.status_code == 400
