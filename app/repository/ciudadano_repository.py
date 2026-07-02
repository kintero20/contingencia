import uuid
import json
import math
from typing import Optional, List, Tuple
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text

from app.models.ciudadano_model import CiudadanoReportado
from config.settings import settings


def _cosine_similarity(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class CiudadanoRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, ciudadano: CiudadanoReportado) -> CiudadanoReportado:
        self.session.add(ciudadano)
        await self.session.commit()
        await self.session.refresh(ciudadano)
        return ciudadano

    async def get_by_id(self, ciudadano_id: uuid.UUID) -> Optional[CiudadanoReportado]:
        result = await self.session.get(CiudadanoReportado, ciudadano_id)
        return result

    async def get_by_cedula(self, cedula: str) -> Optional[CiudadanoReportado]:
        statement = select(CiudadanoReportado).where(
            CiudadanoReportado.cedula == cedula
        )
        result = await self.session.exec(statement)
        return result.first()

    async def update(
        self, ciudadano: CiudadanoReportado
    ) -> CiudadanoReportado:
        self.session.add(ciudadano)
        await self.session.commit()
        await self.session.refresh(ciudadano)
        return ciudadano

    async def delete(self, ciudadano_id: uuid.UUID) -> bool:
        ciudadano = await self.get_by_id(ciudadano_id)
        if ciudadano:
            await self.session.delete(ciudadano)
            await self.session.commit()
            return True
        return False

    async def list_all(
        self, offset: int = 0, limit: int = 100
    ) -> Tuple[List[CiudadanoReportado], int]:
        count_stmt = select(func.count()).select_from(CiudadanoReportado)
        count_result = await self.session.exec(count_stmt)
        total = count_result.one()

        stmt = select(CiudadanoReportado).offset(offset).limit(limit)
        result = await self.session.exec(stmt)
        items = list(result.all())

        return items, total

    async def search_by_facial_similarity(
        self, embedding: list, limite: int = 10, umbral: float = 0.5
    ) -> List[Tuple[CiudadanoReportado, float]]:
        if settings.is_sqlite:
            return await self._search_sqlite(embedding, limite, umbral)
        return await self._search_pgvector(embedding, limite, umbral)

    async def _search_sqlite(
        self, embedding: list, limite: int, umbral: float
    ) -> List[Tuple[CiudadanoReportado, float]]:
        stmt = select(CiudadanoReportado).where(
            CiudadanoReportado.vector_rostro.isnot(None)
        )
        result = await self.session.exec(stmt)
        all_rows = list(result.all())

        scored = []
        for row in all_rows:
            vec = row.get_vector()
            if vec is None:
                continue
            sim = _cosine_similarity(embedding, vec)
            if sim >= umbral:
                scored.append((row, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limite]

    async def _search_pgvector(
        self, embedding: list, limite: int, umbral: float
    ) -> List[Tuple[CiudadanoReportado, float]]:
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        query = text("""
            SELECT id, cedula, nombre, apellido, url_foto,
                   estado_salud, ubicacion_actual,
                   1 - (vector_rostro <=> :embedding) AS similitud
            FROM ciudadanos_reportados
            WHERE vector_rostro IS NOT NULL
              AND 1 - (vector_rostro <=> :embedding) > :umbral
            ORDER BY similitud DESC
            LIMIT :limite
        """)

        result = await self.session.execute(
            query,
            {
                "embedding": embedding_str,
                "umbral": umbral,
                "limite": limite,
            },
        )

        rows = result.fetchall()
        return [(row, row.similitud) for row in rows]
