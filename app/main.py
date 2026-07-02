import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from config.settings import settings
from config.database import init_db, close_db
from app.controllers import ciudadano_controller, busqueda_controller
from app.services.face_service import load_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SBEUP API...")
    await init_db()
    load_model()
    yield
    await close_db()
    logger.info("SBEUP API shut down.")


app = FastAPI(
    title="SBEUP - Sistema Biométrico de Emergencia y Ubicación de Personas",
    description="API humanitaria para registro y localización de personas en contingencias por terremotos",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.static_dir, exist_ok=True)
os.makedirs(settings.upload_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(ciudadano_controller.router)
app.include_router(busqueda_controller.router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/static/index.html")

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
