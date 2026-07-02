import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.schemas import (
    CiudadanoCreate,
    CiudadanoUpdate,
    CiudadanoResponse,
    MensajeResponse,
)
from app.services.ciudadano_service import CiudadanoService
from config.database import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ciudadanos", tags=["Ciudadanos"])


@router.post("/", response_model=CiudadanoResponse, status_code=201)
async def registrar_ciudadano(
    cedula: str = Form(None),
    nombre: str = Form(None),
    apellido: str = Form(None),
    fecha_nacimiento: str = Form(None),
    estado_salud: str = Form(None),
    ubicacion_actual: str = Form(None),
    utm_este: float = Form(None),
    utm_norte: float = Form(None),
    zona_utm: int = Form(None),
    hemisferio: str = Form(None),
    observaciones_medicas: str = Form(None),
    registrado_por: str = Form(None),
    foto: UploadFile = File(None),
    session: AsyncSession = Depends(get_session),
):
    data = CiudadanoCreate(
        cedula=cedula,
        nombre=nombre,
        apellido=apellido,
        fecha_nacimiento=fecha_nacimiento if not fecha_nacimiento else None,
        estado_salud=estado_salud,
        ubicacion_actual=ubicacion_actual,
        utm_este=utm_este,
        utm_norte=utm_norte,
        zona_utm=zona_utm,
        hemisferio=hemisferio,
        observaciones_medicas=observaciones_medicas,
        registrado_por=registrado_por,
    )

    from datetime import date
    if fecha_nacimiento:
        try:
            data.fecha_nacimiento = date.fromisoformat(fecha_nacimiento)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD.")

    foto_bytes = None
    filename = None
    if foto and foto.filename:
        foto_bytes = await foto.read()
        filename = foto.filename

    service = CiudadanoService(session)
    ciudadano = await service.registrar_con_foto(data, foto_bytes, filename)
    return ciudadano


@router.get("/", response_model=List[CiudadanoResponse])
async def listar_ciudadanos(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    service = CiudadanoService(session)
    items, total = await service.listar_ciudadanos(offset, limit)
    return items


@router.get("/{ciudadano_id}", response_model=CiudadanoResponse)
async def obtener_ciudadano(
    ciudadano_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    service = CiudadanoService(session)
    ciudadano = await service.obtener_ciudadano(ciudadano_id)
    if not ciudadano:
        raise HTTPException(status_code=404, detail="Ciudadano no encontrado")
    return ciudadano


@router.put("/{ciudadano_id}", response_model=CiudadanoResponse)
async def actualizar_ciudadano(
    ciudadano_id: uuid.UUID,
    data: CiudadanoUpdate,
    session: AsyncSession = Depends(get_session),
):
    service = CiudadanoService(session)
    ciudadano = await service.actualizar_ciudadano(ciudadano_id, data)
    if not ciudadano:
        raise HTTPException(status_code=404, detail="Ciudadano no encontrado")
    return ciudadano


@router.delete("/{ciudadano_id}", response_model=MensajeResponse)
async def eliminar_ciudadano(
    ciudadano_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    service = CiudadanoService(session)
    eliminado = await service.eliminar_ciudadano(ciudadano_id)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Ciudadano no encontrado")
    return MensajeResponse(mensaje="Ciudadano eliminado correctamente")
