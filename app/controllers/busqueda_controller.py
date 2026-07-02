import logging
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.schemas import (
    CiudadanoResponse,
    CiudadanoSearchResult,
    BusquedaCedulaRequest,
    BusquedaFacialResponse,
)
from app.services.ciudadano_service import CiudadanoService
from config.database import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/busqueda", tags=["Búsqueda"])


@router.get("/cedula/{cedula}", response_model=CiudadanoResponse)
async def buscar_por_cedula(
    cedula: str,
    session: AsyncSession = Depends(get_session),
):
    service = CiudadanoService(session)
    ciudadano = await service.buscar_por_cedula(cedula)
    if not ciudadano:
        raise HTTPException(status_code=404, detail="No se encontró un ciudadano con esa cédula")
    return ciudadano


@router.post("/facial", response_model=BusquedaFacialResponse)
async def buscar_por_rostro(
    foto: UploadFile = File(...),
    limite: int = Query(10, ge=1, le=50),
    umbral: float = Query(0.5, ge=0.0, le=1.0),
    session: AsyncSession = Depends(get_session),
):
    if not foto.filename:
        raise HTTPException(status_code=400, detail="Debe proporcionar una imagen")

    foto_bytes = await foto.read()
    if not foto_bytes:
        raise HTTPException(status_code=400, detail="La imagen está vacía")

    service = CiudadanoService(session)
    resultados = await service.buscar_por_foto(foto_bytes, limite, umbral)

    return BusquedaFacialResponse(
        resultados=resultados,
        total=len(resultados),
    )
