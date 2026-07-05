import io
import pytest
from PIL import Image


pytestmark = pytest.mark.asyncio


async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


async def test_listar_ciudadanos_vacio(client):
    response = await client.get("/ciudadanos/")
    assert response.status_code == 200
    assert response.json() == []


async def test_crear_ciudadano_sin_foto(client):
    response = await client.post("/ciudadanos/", data={
        "cedula": "V12345678",
        "nombre": "Ana",
        "apellido": "Lopez",
        "estado_salud": "estable",
        "ubicacion_actual": "Refugio Los Chorros",
        "utm_este": 289540.0,
        "utm_norte": 1162000.0,
        "zona_utm": 19,
        "hemisferio": "N",
        "observaciones_medicas": "Ninguna",
        "registrado_por": "BRIG01",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "Ana"
    assert data["utm_este"] == 289540.0
    assert data["utm_norte"] == 1162000.0
    assert data["zona_utm"] == 19
    assert data["hemisferio"] == "N"
    assert "id" in data
    return data["id"]


async def test_crear_ciudadano_con_foto(client):
    img = Image.new("RGB", (640, 480), color="gray")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    response = await client.post(
        "/ciudadanos/",
        data={
            "cedula": "V87654321",
            "nombre": "Carlos",
            "apellido": "Mendez",
            "estado_salud": "lesionado",
            "utm_este": 300000.0,
            "utm_norte": 1100000.0,
            "zona_utm": 20,
            "hemisferio": "N",
        },
        files={"foto": ("test.jpg", buf, "image/jpeg")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "Carlos"
    assert data["url_foto"] is not None
    return data["id"]


async def test_obtener_ciudadano(client):
    cid = await test_crear_ciudadano_sin_foto(client)
    response = await client.get(f"/ciudadanos/{cid}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cid
    assert data["nombre"] == "Ana"


async def test_obtener_ciudadano_no_existe(client):
    response = await client.get("/ciudadanos/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_actualizar_ciudadano(client):
    cid = await test_crear_ciudadano_sin_foto(client)
    response = await client.put(f"/ciudadanos/{cid}", json={
        "estado_salud": "critico",
        "observaciones_medicas": "Politraumatizado",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["estado_salud"] == "critico"
    assert data["observaciones_medicas"] == "Politraumatizado"


async def test_eliminar_ciudadano(client):
    cid = await test_crear_ciudadano_sin_foto(client)
    response = await client.delete(f"/ciudadanos/{cid}")
    assert response.status_code == 200
    assert response.json()["mensaje"] == "Ciudadano eliminado correctamente"
    response = await client.get(f"/ciudadanos/{cid}")
    assert response.status_code == 404


async def test_listar_ciudadanos_paginado(client):
    await test_crear_ciudadano_sin_foto(client)
    response = await client.get("/ciudadanos/?offset=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
