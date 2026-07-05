import os
import io
import pytest
import pytest_asyncio
from PIL import Image
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="session", autouse=True)
def _test_env():
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
    os.environ["DATABASE_URL_SYNC"] = "sqlite://"
    yield
    del os.environ["DATABASE_URL"]
    del os.environ["DATABASE_URL_SYNC"]


@pytest.fixture(scope="session")
def app():
    from app.main import app
    return app


@pytest_asyncio.fixture(autouse=True)
async def _db():
    from config.database import init_db, close_db
    await init_db()
    yield
    await close_db()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def sample_image():
    img = Image.new("RGB", (640, 480), color="gray")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf
