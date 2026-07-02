import uuid
import json
from datetime import datetime, date
from typing import Optional
from uuid import UUID
from sqlmodel import SQLModel, Field
from sqlalchemy import TypeDecorator, VARCHAR, TEXT, String
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

    id: UUID = Field(
        default_factory=uuid.uuid4,
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
    utm_este: Optional[float] = Field(default=None, description="Coordenada UTM Este (X)")
    utm_norte: Optional[float] = Field(default=None, description="Coordenada UTM Norte (Y)")
    zona_utm: Optional[int] = Field(default=None, description="Zona UTM (18-20 para Venezuela)")
    hemisferio: Optional[str] = Field(default=None, max_length=1, description="N o S")
    observaciones_medicas: Optional[str] = Field(default=None)
    registrado_por: Optional[str] = Field(default=None, max_length=100)
    creado_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )

    def get_vector(self) -> Optional[list]:
        if self.vector_rostro is None:
            return None
        if isinstance(self.vector_rostro, str):
            return json.loads(self.vector_rostro)
        return self.vector_rostro

    def set_vector(self, vector: Optional[list]):
        if vector is not None:
            self.vector_rostro = json.dumps(vector)
        else:
            self.vector_rostro = None
