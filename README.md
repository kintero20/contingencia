# contingencia
# INFORME TÉCNICO - SBEUP
## Sistema Biométrico de Emergencia y Ubicación de Personas

**Versión:** 1.0.0  
**Fecha:** Julio 2026  
**Propósito:** Registro y localización de personas en contingencias por terremotos en Venezuela

---

## 1. REQUERIMIENTOS Y CONSIDERACIONES DE DISEÑO

### 1.1 Contexto del Problema

Venezuela es un país de alta sismicidad (Anillos de Fuego del Pacífico). Un terremoto de gran magnitud en una zona densamente poblada como Caracas, Maracaibo o Valencia generaría:

- Decenas de miles de desplazados y heridos
- Saturación de hospitales, refugios y centros de acopio
- Fallas eléctricas y de conectividad prolongadas
- Dificultad para que familiares localicen a sus seres queridos
- Necesidad de identificación de personas inconscientes o sin documentos

### 1.2 Requerimientos Funcionales

| # | Requerimiento | Prioridad |
|---|---|---|
| RF-01 | Registrar persona con datos básicos + foto + ubicación | Crítica |
| RF-02 | Buscar persona por número de cédula | Crítica |
| RF-03 | Buscar persona por reconocimiento facial (personas inconscientes, NN) | Alta |
| RF-04 | Visualizar detalle completo de la persona registrada | Alta |
| RF-05 | Listar todos los registros con paginación | Media |
| RF-06 | Actualizar datos de una persona (ej: cambio de estado de salud) | Alta |
| RF-07 | Eliminar registros (depuración) | Media |
| RF-08 | Interfaz mobile-first usable en condiciones adversas (poca luz, pantalla pequeña) | Crítica |

### 1.3 Requerimientos No Funcionales

| # | Requerimiento | Detalle |
|---|---|---|
| RNF-01 | Disponibilidad | Debe operar 24/7 incluso con cortes eléctricos parciales |
| RNF-02 | Rendimiento | Búsqueda facial < 5 segundos con hasta 50,000 registros |
| RNF-03 | Offline-first | La app móvil debe funcionar sin conexión, sincronizando cuando haya red |
| RNF-04 | Ancho de banda mínimo | Transmisión de solo vectores faciales (~2 KB), no imágenes crudas |
| RNF-05 | Escalabilidad horizontal | FastAPI asíncrono permite múltiples workers |
| RNF-06 | Seguridad | CORS configurable, UUIDs no secuenciales, sin exposición de datos sensibles |
| RNF-07 | Portabilidad | Despliegue en Windows (desarrollo) y Linux (producción) |

### 1.4 Restricciones del Entorno

- **Conectividad:** Internet intermitente y de baja velocidad (proxy corporativo)
- **Hardware:** Servidores sin GPU, CPUs genéricas
- **Energía:** Cortes eléctricos frecuentes (Apagones programados)
- **Usuarios:** Brigadistas con formación técnica básica, no ingenieros
- **Dispositivos:** Teléfonos Android gama media-baja, sin Google Services avanzados

### 1.5 Decisiones Arquitectónicas Clave

| Decisión | Alternativa | Justificación |
|---|---|---|
| **SQLite en desarrollo** vs PostgreSQL+pgvector | SQLite | Proxy corporativo impide instalar dependencias pesadas (psycopg2, pgvector). SQLite es autónomo, cero configuración. El código está preparado para migrar a PostgreSQL cambiando la URL. |
| **UTM** vs Lat/Lng decimales | UTM | Los brigadistas en terreno usan mapas impresos con cuadrículas UTM. Es más intuitivo dar una zona + coordenadas en metros que grados decimales. |
| **InsightFace CPU** vs GPU | CPU | Sin GPU disponible en servidores de contingencia. InsightFace con ONNX Runtime CPU es suficientemente rápido para uso humanitario. |
| **PWA Vanilla** vs React/Vue/Angular | Vanilla JS | Sin build tools, sin node_modules, sin compilación. Se sirve directamente desde FastAPI. Un solo HTML que funciona offline con Service Worker. |
| **FastAPI asíncrono** vs Flask/Django | FastAPI | Soporte nativo de async/await para I/O concurrente (múltiples refugios subiendo datos simultáneamente). Documentación Swagger automática. Validación con Pydantic. |
| **Embedding como JSON** vs pgvector | JSON texto | SQLite no soporta pgvector. Se almacena el vector 512-d como JSON TEXT. En producción con PostgreSQL se usa la columna vector(512) nativa con índice HNSW. |

---

## 2. ARQUITECTURA DEL BACKEND

### 2.1 Patrón MVC + Servicios (MVC+S)

```
app/
├── main.py                 # Punto de entrada, lifespan, middlewares
├── controllers/            # Capa HTTP (routers FastAPI)
│   ├── ciudadano_controller.py
│   └── busqueda_controller.py
├── services/               # Lógica de negocio + IA
│   ├── ciudadano_service.py
│   └── face_service.py
├── models/                 # Entidades SQLModel + DTOs Pydantic
│   ├── ciudadano_model.py
│   └── schemas.py
├── repository/             # Acceso a base de datos
│   └── ciudadano_repository.py
config/                     # Configuración global
├── settings.py             # Pydantic Settings, .env
└── database.py             # Engines, sesiones, init_db
```

**Flujo de una petición típica:**

```
Cliente HTTP → FastAPI Router → Controller (valida input)
  → Service (lógica de negocio, llama a IA si aplica)
    → Repository (SQLModel queries)
      → Database (SQLite / PostgreSQL)
    ← Modelo ORM
  ← DTO Pydantic
← JSON Response
```

### 2.2 Configuración Centralizada (`config/settings.py`)

Usa `pydantic-settings` para leer desde `.env` con defaults inteligentes:

```python
database_url: str = "sqlite+aiosqlite:///./sbeup.db"     # Dev por defecto
database_url_sync: str = "sqlite:///./sbeup.db"           # Sync para Alembic
api_host: str = "0.0.0.0"
api_port: int = 8000
api_debug: bool = True
cors_origins: str = '["*"]'                               # JSON string
upload_dir: str = "uploads"
static_dir: str = "static"
```

Propiedades computadas:
- `cors_origins_list` → parsea el JSON string a lista
- `is_sqlite` → detecta si la URL contiene "sqlite" para decisiones condicionales

### 2.3 Conexión a Base de Datos (`config/database.py`)

Dos engines asíncronos y síncronos para compatibilidad:

```python
# Asíncrono (FastAPI runtime)
engine = create_async_engine(database_url, echo=debug, connect_args={...})
async_session = async_sessionmaker(engine, class_=AsyncSession)

# Síncrono (scripts, Alembic migrations)
engine_sync = create_sync_engine(database_url_sync, ...)
SessionLocal = sessionmaker(bind=engine_sync)
```

**`init_db()`**: Crea todas las tablas (`SQLModel.metadata.create_all`) y opcionalmente habilita la extensión `vector` en PostgreSQL.

**`get_session()`**: Generador asíncrono para inyección de dependencias en FastAPI.

### 2.4 Punto de Entrada (`app/main.py`)

```python
@asynccontextmanager
async def lifespan(app):
    await init_db()         # Crear tablas al iniciar
    load_model()            # Cargar InsightFace (en background thread)
    yield
    await close_db()        # Cerrar conexiones al apagar
```

Middlewares y montajes:
- **CORS**: Orígenes configurable desde `.env`
- **Static Files**: `/static` → interfaz PWA, `/uploads` → fotos
- **Redirect**: `GET /` → `/static/index.html`

### 2.5 Capa de Controllers

#### `ciudadano_controller.py` — CRUD de ciudadanos

| Método | Ruta | Función |
|---|---|---|
| POST | `/ciudadanos/` | Crear persona con foto (multipart/form-data) |
| GET | `/ciudadanos/` | Listar todos (paginado: offset/limit) |
| GET | `/ciudadanos/{id}` | Obtener por UUID |
| PUT | `/ciudadanos/{id}` | Actualizar campos (PATCH-style) |
| DELETE | `/ciudadanos/{id}` | Eliminar |

El POST es **multipart** porque recibe tanto datos estructurados (form fields) como archivos (foto). Los parámetros opcionales usan `Form(None)`.

#### `busqueda_controller.py` — Búsquedas especializadas

| Método | Ruta | Función |
|---|---|---|
| GET | `/busqueda/cedula/{cedula}` | Búsqueda exacta por cédula |
| POST | `/busqueda/facial` | Búsqueda por similitud facial (subir foto) |

### 2.6 Capa de Servicios

#### `ciudadano_service.py`

**`registrar_con_foto()`**:
1. Si hay foto → extrae embedding facial (512-d normalizado) via `face_service`
2. Genera UUID para el nombre de archivo, lo guarda en `uploads/`
3. Crea instancia de `CiudadanoReportado` con el embedding serializado
4. Delega en `CiudadanoRepository.create()`

**`buscar_por_foto()`**:
1. Extrae embedding de la foto subida
2. Delega en repositorio: `search_by_facial_similarity()`
3. Convierte resultados (row, similitud) a `CiudadanoSearchResult` DTOs
4. Retorna lista ordenada por similitud descendente

#### `face_service.py`

**Estrategia de carga perezosa (lazy loading):**

```python
_face_model = None
_face_detector = None
_model_loading = False
```

- `load_model()`: Verifica si los modelos ONNX existen en `~/.insightface/models/buffalo_l/`. Si no existen, lanza un thread de descarga en segundo plano para no bloquear el startup del servidor.
- `_init_face_models()`: Inicializa `FaceAnalysis` con `CPUExecutionProvider`, prepara detector en tamaño 640x640.
- `extract_embedding()` / `extract_embedding_from_bytes()`: Lee imagen, convierte BGR→RGB, detecta rostros, extrae embedding del primer rostro detectado, normaliza (L2), retorna como lista de floats.

**Manejo de errores graceful:** Si InsightFace no está instalado, si falla la descarga de modelos, o si no se detecta rostro, retorna `None` sin romper la aplicación.

### 2.7 Capa de Repositorio

#### `ciudadano_repository.py`

```python
class CiudadanoRepository:
    async def create(self, ciudadano) -> CiudadanoReportado
    async def get_by_id(self, id) -> Optional[CiudadanoReportado]
    async def get_by_cedula(self, cedula) -> Optional[CiudadanoReportado]
    async def update(self, ciudadano) -> CiudadanoReportado
    async def delete(self, id) -> bool
    async def list_all(self, offset, limit) -> Tuple[List, int]
    async def search_by_facial_similarity(self, embedding, limite, umbral) -> List[Tuple]
```

**Búsqueda facial con dos dialectos:**

```python
async def search_by_facial_similarity(self, embedding, limite, umbral):
    if settings.is_sqlite:
        return await self._search_sqlite(embedding, limite, umbral)
    return await self._search_pgvector(embedding, limite, umbral)
```

- **SQLite**: Carga todos los registros con vector no nulo, calcula similitud coseno en Python puro, filtra por umbral, ordena y limita.
- **PostgreSQL+pgvector**: Usa el operador `<=>` (distancia coseno) con índice HNSW para búsqueda sub-segundo en millones de registros.

**Fórmula de similitud coseno:**

```python
def _cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0
```

---

## 3. MODELO DE BASE DE DATOS

### 3.1 Esquema Actual (SQLite)

```sql
CREATE TABLE ciudadanos_reportados (
    id              UUID PRIMARY KEY,
    cedula          VARCHAR(20) UNIQUE,
    nombre          VARCHAR(100),
    apellido        VARCHAR(100),
    fecha_nacimiento DATE,
    vector_rostro   TEXT,               -- JSON con embedding 512 floats
    url_foto        TEXT,
    estado_salud    VARCHAR(50),        -- estable, lesionado, critico, fallecido
    ubicacion_actual TEXT,
    utm_este        REAL,               -- Coordenada UTM Este (X) en metros
    utm_norte       REAL,               -- Coordenada UTM Norte (Y) en metros
    zona_utm        INTEGER,            -- Zona UTM (18-21 para Venezuela)
    hemisferio      VARCHAR(1),         -- 'N' o 'S'
    observaciones_medicas TEXT,
    registrado_por  VARCHAR(100),
    creado_at       TIMESTAMP,
    updated_at      TIMESTAMP
);
```

### 3.2 Esquema Producción (PostgreSQL + pgvector)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE ciudadanos_reportados (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- ... mismos campos ...
    vector_rostro   vector(512),         -- Columna vectorial nativa
    -- ... mismos campos UTM ...
    creado_at       TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON ciudadanos_reportados
    USING hnsw (vector_rostro vector_cosine_ops);
```

### 3.3 VectorJson TypeDecorator

Para almacenar vectores como JSON en SQLite y como columna `vector(512)` en PostgreSQL:

```python
class VectorJson(TypeDecorator):
    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return json.dumps(value) if isinstance(value, list) else value

    def process_result_value(self, value, dialect):
        return json.loads(value) if isinstance(value, str) else value
```

### 3.4 Campos UTM vs Lat/Lng

| Campo | Tipo | Ejemplo | Descripción |
|---|---|---|---|
| `utm_este` | REAL | 289540.0 | Coordenada Este (X) en metros |
| `utm_norte` | REAL | 1162000.0 | Coordenada Norte (Y) en metros |
| `zona_utm` | INTEGER | 19 | Zona UTM (Venezuela: 18-21) |
| `hemisferio` | VARCHAR(1) | N | 'N' para Norte, 'S' para Sur |

**Venezuela está en las zonas UTM 18, 19, 20 y 21, hemisferio Norte.**

---

## 4. API REST

### 4.1 Especificación OpenAPI

FastAPI genera documentación Swagger automática en `/docs` (OpenAPI 3.0).

### 4.2 Endpoints Detallados

#### `GET /health`
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

#### `POST /ciudadanos/`
- **Content-Type:** `multipart/form-data`
- **Campos del formulario:**
  - `cedula` (string, opcional)
  - `nombre` (string, opcional)
  - `apellido` (string, opcional)
  - `fecha_nacimiento` (string ISO date, opcional)
  - `estado_salud` (string, opcional)
  - `ubicacion_actual` (string, opcional)
  - `utm_este` (number, opcional)
  - `utm_norte` (number, opcional)
  - `zona_utm` (integer, opcional)
  - `hemisferio` (string "N"/"S", opcional)
  - `observaciones_medicas` (string, opcional)
  - `registrado_por` (string, opcional)
- **Archivo:** `foto` (image, opcional)
- **Response:** `201 Created` con `CiudadanoResponse`

#### `GET /ciudadanos/?offset=0&limit=100`
- Lista paginada de ciudadanos
- **Response:** Array de `CiudadanoResponse`

#### `GET /ciudadanos/{id}`
- Detalle por UUID
- **Response:** `CiudadanoResponse`
- **Error:** `404` si no existe

#### `PUT /ciudadanos/{id}`
- Actualización parcial (solo campos enviados)
- **Content-Type:** `application/json`
- **Body:** `CiudadanoUpdate` (todos los campos opcionales)
- **Response:** `CiudadanoResponse` actualizado

#### `DELETE /ciudadanos/{id}`
- **Response:** `{"mensaje": "Ciudadano eliminado correctamente"}`

#### `GET /busqueda/cedula/{cedula}`
- Búsqueda exacta (case-sensitive) por cédula
- **Response:** `CiudadanoResponse`
- **Error:** `404` si no se encuentra

#### `POST /busqueda/facial`
- **Content-Type:** `multipart/form-data`
- **Archivo:** `foto` (image, obligatorio)
- **Query params:** `limite=10` (1-50), `umbral=0.5` (0.0-1.0)
- **Response:**
```json
{
  "resultados": [
    {
      "id": "uuid",
      "cedula": "V12345678",
      "nombre": "Ana",
      "apellido": "Lopez",
      "url_foto": "uploads/xxx.jpg",
      "estado_salud": "estable",
      "ubicacion_actual": "Refugio Los Chorros",
      "similitud": 0.9723
    }
  ],
  "total": 1
}
```

### 4.3 DTOs (Pydantic Models)

| DTO | Uso |
|---|---|
| `CiudadanoCreate` | Crear registro (todos opcionales) |
| `CiudadanoUpdate` | Actualizar (todos opcionales, `exclude_unset`) |
| `CiudadanoResponse` | Respuesta completa (`from_attributes=True`) |
| `CiudadanoSearchResult` | Resultado de búsqueda facial (incluye `similitud`) |
| `BusquedaFacialResponse` | Envoltorio con `resultados[]` y `total` |
| `MensajeResponse` | Mensajes simples `{"mensaje": "..."}` |

---

## 5. RECONOCIMIENTO FACIAL

### 5.1 Pipeline de Extracción

```
Imagen (JPEG/PNG)
  → OpenCV (imdecode o imread)
    → BGR → RGB
      → InsightFace FaceAnalysis.get()
        → Detección de rostros (RetinaFace)
          → Extracción de embedding (ArcFace 512-d)
            → Normalización L2 (||v|| = 1)
              → Lista de 512 floats → JSON
```

### 5.2 InsightFace: Modelo buffalo_l

- **Detector:** RetinaFace (detección de rostros con landmarks)
- **Reconocedor:** ArcFace (embedding de 512 dimensiones)
- **Tamaño:** ~275 MB (descargado una vez, cacheado en `~/.insightface/models/buffalo_l/`)
- **Proveedor:** ONNX Runtime con `CPUExecutionProvider`
- **Tamaño de detección:** 640×640 píxeles

### 5.3 Estrategia de Carga

Para no bloquear el startup del servidor:

```
load_model() → ¿Modelos descargados?
  ├── No → thread background descarga desde internet
  └── Sí → FaceAnalysis(preparar, det_size=640)
              ↓
         _face_model y _face_detector globales
```

### 5.4 Búsqueda por Similitud

**SQLite (desarrollo):**
```python
for cada registro con vector:
    sim = cosine_similarity(embedding_query, vector)
    if sim >= umbral:
        agregar a resultados
ordenar por similitud DESC
tomar primeros N
```
- Complejidad: O(n) donde n = registros con vector
- Aceptable hasta ~50,000 registros

**PostgreSQL+pgvector (producción):**
```sql
SELECT *, 1 - (vector_rostro <=> :embedding) AS similitud
FROM ciudadanos_reportados
WHERE 1 - (vector_rostro <=> :embedding) > :umbral
ORDER BY similitud DESC
LIMIT :limite
```
- Usa índice HNSW (Hierarchical Navigable Small World)
- Complejidad: O(log n) — milisegundos con millones de registros

### 5.5 Normalización L2

El embedding se normaliza antes de almacenar para que la similitud coseno sea equivalente al producto punto:

```python
norm = np.linalg.norm(embedding)
if norm > 0:
    embedding = embedding / norm
```

Con vectores normalizados: `cosine_similarity(a, b) = dot(a, b)`

---

## 6. FRONTEND (PWA)

### 6.1 Stack

- **HTML5** semántico
- **CSS3** con variables, Grid, Flexbox, media queries (light/dark mode)
- **JavaScript Vanilla** (ES6+) sin frameworks, sin bundlers, sin npm
- **PWA-ready**: `theme-color`, `apple-mobile-web-app-capable`, `viewport` optimizado
- **Single-file**: todo el frontend en un solo `index.html` (~400 líneas)

### 6.2 Estructura de la Interfaz (SPA)

```
Pantallas:
├── Inicio (home)
│   ├── Estadísticas (registrados totales, registros hoy)
│   └── Últimos registros
├── Registrar (register)
│   ├── Datos personales (cédula, nombre, apellido, fecha nac.)
│   ├── Foto (cámara + galería)
│   └── Situación (salud, ubicación, UTM, observaciones)
├── Buscar (search)
│   ├── Por cédula
│   └── Por foto (reconocimiento facial)
└── Detalle (detail)
    └── Info completa de la persona + coordenadas UTM

Navegación inferior fija (bottom-nav):
[🏠 Inicio] [➕ Registrar] [🔍 Buscar]
```

### 6.3 Funcionalidades Clave

#### Cámara
```html
<input type="file" accept="image/*" capture="environment">
```
- En dispositivos móviles abre la cámara trasera directamente
- Fallback a selector de archivos en desktop
- Previsualización instantánea con FileReader

#### GPS → UTM
```javascript
navigator.geolocation.getCurrentPosition(
  p => {
    const utm = latLngToUtm(p.coords.latitude, p.coords.longitude);
    // Rellena automáticamente: utm_este, utm_norte, zona_utm, hemisferio
  }
)
```

**Algoritmo de conversión Lat/Lng → UTM** implementado en JavaScript puro:
- Elipsoide WGS84 (a=6378137, f=1/298.257223563)
- Cálculo de zona UTM (6° por zona)
- Meridiano central
- Fórmulas de Carroll (proyección transversa de Mercator)

#### Búsqueda Facial
1. Usuario toma/elige foto
2. Se envía a `POST /busqueda/facial` como multipart
3. Backend extrae embedding y busca coincidencias
4. Resultados se muestran con nombre, cédula, ubicación y porcentaje de similitud

#### Estados de Salud con Colores
```css
.status-estable  { background: #dcfce7; color: #166534; }  /* Verde */
.status-lesionado { background: #fee2e2; color: #991b1b; } /* Rojo */
.status-critico  { background: #fef3c7; color: #92400e; }   /* Naranja */
.status-fallecido { background: #f3f4f6; color: #374151; }  /* Gris */
```

### 6.4 Experiencia Móvil

- **Safe area**: `padding-bottom: env(safe-area-inset-bottom)` para notch
- **Touch**: `-webkit-tap-highlight-color: transparent`, `:active` states
- **Dark mode**: `@media(prefers-color-scheme:dark)` con variables CSS
- **Sin scroll horizontal**: `max-width: 480px`, `margin: 0 auto`
- **Fuentes nativas**: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto`
- **Animaciones**: `@keyframes fadeIn` para toasts, `@keyframes spin` para loading

---

## 7. PRUEBAS

### 7.1 Configuración

- **Framework:** pytest + pytest-asyncio + httpx
- **Base de datos en memoria:** SQLite (`sqlite+aiosqlite://`)
- **Fixtures:** Cliente HTTP asíncrono, sesión de base de datos aislada

### 7.2 Pruebas Implementadas

| Test | Descripción |
|---|---|
| `test_health_check` | Verifica que `GET /health` retorna 200 con `{"status": "ok"}` |
| `test_listar_ciudadanos_vacio` | Lista vacía retorna `[]` |
| `test_buscar_por_cedula_no_encontrada` | Cédula inexistente retorna 404 |

### 7.3 Pruebas Pendientes

| Test | Prioridad |
|---|---|
| Registrar con foto y verificar embedding | Alta |
| Búsqueda facial con foto conocida | Alta |
| CRUD completo (crear, obtener, actualizar, eliminar) | Alta |
| Campos UTM en creación y lectura | Media |
| Paginación con offset/limit | Media |
| Actualización parcial (PATCH semantics) | Media |
| Búsqueda facial con umbral y límite | Media |
| Registro sin foto (solo datos) | Media |

---

## 8. DESPLIEGUE

### 8.1 Desarrollo (Local)

```bash
# Clonar e instalar dependencias
pip install -r requirements.txt

# Iniciar servidor
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Acceder
# API:       http://127.0.0.1:8000
# Swagger:   http://127.0.0.1:8000/docs
# Frontend:  http://127.0.0.1:8000/
```

### 8.2 Producción (PostgreSQL + pgvector)

```bash
# Iniciar base de datos
docker-compose up -d

# Configurar .env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/sbeup
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/sbeup

# Iniciar con Gunicorn + Uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

# Proxy inverso (Nginx recomendado)
```

### 8.3 Docker Compose (Producción)

```yaml
services:
  db:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: sbeup
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
```

---

## 9. DEPENDENCIAS

### 9.1 Producción

| Paquete | Versión | Propósito |
|---|---|---|
| `fastapi` | 0.115.6 | Framework web asíncrono |
| `uvicorn[standard]` | 0.34.0 | Servidor ASGI |
| `sqlmodel` | 0.0.22 | ORM + Pydantic (SQLAlchemy) |
| `aiosqlite` | 0.20.0 | SQLite asíncrono |
| `python-multipart` | 0.0.19 | Parseo de formularios multipart |
| `python-dotenv` | 1.0.1 | Carga de .env |
| `pydantic-settings` | 2.7.0 | Configuración tipada |
| `insightface` | 1.0.1 | Detección y reconocimiento facial |
| `opencv-python` | 4.13.0.92 | Procesamiento de imágenes |
| `onnxruntime` | 1.27.0 | Motor de inferencia ONNX |
| `numpy` | >=2.0.0 | Algebra lineal (vectores, embeddings) |
| `Pillow` | 11.1.0 | Procesamiento de imágenes alternativo |
| `alembic` | 1.14.0 | Migraciones de base de datos |

### 9.2 Desarrollo/Testing

| Paquete | Versión | Propósito |
|---|---|---|
| `httpx` | 0.28.1 | Cliente HTTP asíncrono para tests |
| `pytest` | 8.3.4 | Framework de pruebas |
| `pytest-asyncio` | 0.24.0 | Soporte async para pytest |

### 9.3 Producción (PostgreSQL)

| Paquete | Propósito |
|---|---|
| `asyncpg` | Driver PostgreSQL asíncrono |
| `psycopg2-binary` | Driver PostgreSQL síncrono |
| `pgvector` | Extension vector para PostgreSQL |

---

## 10. ESTRUCTURA DEL PROYECTO

```
C:\wamp64\www\Desarrollos\Contingencia\
│
├── app/                          # Código principal
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, lifespan, middlewares
│   ├── controllers/              # Routers HTTP
│   │   ├── __init__.py
│   │   ├── ciudadano_controller.py
│   │   └── busqueda_controller.py
│   ├── services/                 # Lógica de negocio
│   │   ├── __init__.py
│   │   ├── ciudadano_service.py
│   │   └── face_service.py       # InsightFace + OpenCV
│   ├── models/                   # Entidades y DTOs
│   │   ├── __init__.py
│   │   ├── ciudadano_model.py    # SQLModel + VectorJson
│   │   └── schemas.py            # Pydantic DTOs
│   └── repository/               # Acceso a datos
│       ├── __init__.py
│       └── ciudadano_repository.py
│
├── config/                       # Configuración global
│   ├── __init__.py
│   ├── settings.py               # Pydantic Settings
│   └── database.py               # Engines, sesiones, init_db
│
├── static/                       # Frontend PWA
│   └── index.html                # App completa (HTML+CSS+JS)
│
├── uploads/                      # Fotos subidas (gitignored)
│
├── tests/                        # Pruebas
│   ├── __init__.py
│   ├── conftest.py               # Fixtures (cliente, BD)
│   └── test_api.py               # Tests de integración
│
├── .env                          # Variables de entorno
├── .env.example                  # Template de .env
├── .gitignore
├── docker-compose.yml            # PostgreSQL + pgvector
├── pytest.ini                    # Config pytest
├── requirements.txt              # Dependencias Python
└── README.md                     # Documentación inicial
```

---

## 11. MÉTRICAS Y RENDIMIENTO

| Operación | Tiempo estimado (SQLite, 10K registros) | Tiempo estimado (PostgreSQL+pgvector, 1M registros) |
|---|---|---|
| Registrar sin foto | < 50 ms | < 20 ms |
| Registrar con foto + embedding | ~500 ms | ~500 ms (misma CPU) |
| Buscar por cédula | < 20 ms | < 10 ms (índice B-tree) |
| Buscar facial (top-10) | ~200 ms (escaneo secuencial) | < 10 ms (índice HNSW) |
| Listar (offset/limit) | < 30 ms | < 20 ms |

**Cuello de botella actual:** Extracción de embedding (InsightFace CPU). Depende de la CPU del servidor.

**Estrategia de mejora:** En producción con alta concurrencia, usar workers separados para inferencia o migrar a GPU si está disponible.

---

## 12. SEGURIDAD Y BUENAS PRÁCTICAS

- **UUID v4** como IDs (no secuenciales, no adivinables)
- **Validación de entrada** con Pydantic (tipos, formatos, rangos)
- **CORS configurable** desde variables de entorno
- **Sin exposición de secrets**: `.env` en `.gitignore`
- **Nombres de archivo con UUID**: evita colisiones y path traversal
- **Manejo graceful de errores**: la app no crashea si falla el reconocimiento facial
- **Logging estructurado**: con módulo `logging` estándar, niveles INFO/ERROR
