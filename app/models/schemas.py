from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CiudadanoCreate(BaseModel):
    cedula: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    estado_salud: Optional[str] = None
    ubicacion_actual: Optional[str] = None
    utm_este: Optional[float] = None
    utm_norte: Optional[float] = None
    zona_utm: Optional[int] = None
    hemisferio: Optional[str] = None
    observaciones_medicas: Optional[str] = None
    registrado_por: Optional[str] = None


class CiudadanoUpdate(BaseModel):
    cedula: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    estado_salud: Optional[str] = None
    ubicacion_actual: Optional[str] = None
    utm_este: Optional[float] = None
    utm_norte: Optional[float] = None
    zona_utm: Optional[int] = None
    hemisferio: Optional[str] = None
    observaciones_medicas: Optional[str] = None
    registrado_por: Optional[str] = None


class CiudadanoResponse(BaseModel):
    id: str
    cedula: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    url_foto: Optional[str] = None
    estado_salud: Optional[str] = None
    ubicacion_actual: Optional[str] = None
    utm_este: Optional[float] = None
    utm_norte: Optional[float] = None
    zona_utm: Optional[int] = None
    hemisferio: Optional[str] = None
    observaciones_medicas: Optional[str] = None
    registrado_por: Optional[str] = None
    creado_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CiudadanoSearchResult(BaseModel):
    id: str
    cedula: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    url_foto: Optional[str] = None
    estado_salud: Optional[str] = None
    ubicacion_actual: Optional[str] = None
    similitud: Optional[float] = None

    model_config = {"from_attributes": True}


class BusquedaCedulaRequest(BaseModel):
    cedula: str = Field(..., min_length=1, max_length=20)


class BusquedaFacialResponse(BaseModel):
    resultados: List[CiudadanoSearchResult]
    total: int


class MensajeResponse(BaseModel):
    mensaje: str
