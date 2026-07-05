import uuid
import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.ciudadano_model import CiudadanoReportado
from app.models.schemas import (
    CiudadanoCreate,
    CiudadanoUpdate,
    CiudadanoSearchResult,
)
from app.repository.ciudadano_repository import CiudadanoRepository
from app.services.face_service import extract_embedding_from_bytes
from config.settings import settings

logger = logging.getLogger(__name__)


class CiudadanoService:

    def __init__(self, session: AsyncSession):
        self.repo = CiudadanoRepository(session)

    async def registrar_con_foto(
        self,
        data: CiudadanoCreate,
        foto_bytes: bytes,
        filename: str,
    ) -> CiudadanoReportado:
        embedding = None
        url_foto = None

        if foto_bytes:
            embedding = extract_embedding_from_bytes(foto_bytes)

            upload_dir = settings.upload_dir
            os.makedirs(upload_dir, exist_ok=True)

            ext = os.path.splitext(filename)[1] or ".jpg"
            foto_filename = f"{uuid.uuid4()}{ext}"
            foto_path = os.path.join(upload_dir, foto_filename)

            with open(foto_path, "wb") as f:
                f.write(foto_bytes)

            url_foto = foto_path

        ciudadano = CiudadanoReportado(
            cedula=data.cedula,
            nombre=data.nombre,
            apellido=data.apellido,
            fecha_nacimiento=data.fecha_nacimiento,
            url_foto=url_foto,
            estado_salud=data.estado_salud,
            ubicacion_actual=data.ubicacion_actual,
            utm_este=data.utm_este,
            utm_norte=data.utm_norte,
            zona_utm=data.zona_utm,
            hemisferio=data.hemisferio,
            observaciones_medicas=data.observaciones_medicas,
            registrado_por=data.registrado_por,
        )
        ciudadano.set_vector(embedding)

        return await self.repo.create(ciudadano)

    async def buscar_por_cedula(
        self, cedula: str
    ) -> Optional[CiudadanoReportado]:
        return await self.repo.get_by_cedula(cedula)

    async def buscar_por_foto(
        self, foto_bytes: bytes, limite: int = 10, umbral: float = 0.5
    ) -> List[CiudadanoSearchResult]:
        embedding = extract_embedding_from_bytes(foto_bytes)
        if embedding is None:
            return []

        results = await self.repo.search_by_facial_similarity(
            embedding, limite, umbral
        )

        search_results = []
        for row, similitud in results:
            search_results.append(
                CiudadanoSearchResult(
                    id=row.id,
                    cedula=row.cedula,
                    nombre=row.nombre,
                    apellido=row.apellido,
                    url_foto=row.url_foto,
                    estado_salud=row.estado_salud,
                    ubicacion_actual=row.ubicacion_actual,
                    similitud=round(similitud, 4),
                )
            )

        return search_results

    async def obtener_ciudadano(
        self, ciudadano_id: str
    ) -> Optional[CiudadanoReportado]:
        return await self.repo.get_by_id(ciudadano_id)

    async def actualizar_ciudadano(
        self, ciudadano_id: str, data: CiudadanoUpdate
    ) -> Optional[CiudadanoReportado]:
        ciudadano = await self.repo.get_by_id(ciudadano_id)
        if not ciudadano:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(ciudadano, field, value)

        ciudadano.updated_at = datetime.now(timezone.utc)
        return await self.repo.update(ciudadano)

    async def eliminar_ciudadano(
        self, ciudadano_id: str
    ) -> bool:
        return await self.repo.delete(ciudadano_id)

    async def listar_ciudadanos(
        self, offset: int = 0, limit: int = 100
    ) -> Tuple[List[CiudadanoReportado], int]:
        return await self.repo.list_all(offset, limit)
