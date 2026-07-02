import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _test_db():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
    os.environ["DATABASE_URL_SYNC"] = "sqlite://"
    yield
    del os.environ["DATABASE_URL"]
    del os.environ["DATABASE_URL_SYNC"]


@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_image():
    import io
    from PIL import Image

    img = Image.new("RGB", (640, 480), color="gray")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf
