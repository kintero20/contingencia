import uuid
import json
from datetime import datetime, date, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import TypeDecorator, VARCHAR, TEXT
from sqlalchemy.dialects.sqlite import TEXT as SQLITE_TEXT

from config.settings import settings


class VectorJson(TypeDecorator):
    impl = TEXT
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(SQLITE_TEXT())
        return dialect.type_descriptor(VARCHAR(4096))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, list):
            return json.dumps(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        return value


class CiudadanoReportado(SQLModel, table=True):
    __tablename__ = "ciudadanos_reportados"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        nullable=False,
    )
    cedula: Optional[str] = Field(default=None, max_length=20, unique=True)
    nombre: Optional[str] = Field(default=None, max_length=100)
    apellido: Optional[str] = Field(default=None, max_length=100)
    fecha_nacimiento: Optional[date] = Field(default=None)
    vector_rostro: Optional[str] = Field(
        default=None,
        sa_type=VectorJson,
    )
    url_foto: Optional[str] = Field(default=None)
    estado_salud: Optional[str] = Field(default=None, max_length=50)
    ubicacion_actual: Optional[str] = Field(default=None)
    utm_este: Optional[float] = Field(default=None)
    utm_norte: Optional[float] = Field(default=None)
    zona_utm: Optional[int] = Field(default=None)
    hemisferio: Optional[str] = Field(default=None, max_length=1)
    observaciones_medicas: Optional[str] = Field(default=None)
    registrado_por: Optional[str] = Field(default=None, max_length=100)
    creado_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    def get_vector(self):
        if self.vector_rostro is None:
            return None
        if isinstance(self.vector_rostro, str):
            return json.loads(self.vector_rostro)
        return self.vector_rostro

    def set_vector(self, vector):
        if vector is not None:
            self.vector_rostro = json.dumps(vector)
        else:
            self.vector_rostro = None
