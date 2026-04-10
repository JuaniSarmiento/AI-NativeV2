# Migraciones de Base de Datos — Plataforma AI-Native

**Última actualización**: 2026-04-10
**Audiencia**: desarrolladores del proyecto
**Clasificación**: Documentación interna — infraestructura

---

## Índice

1. [Arquitectura multi-schema de PostgreSQL](#1-arquitectura-multi-schema)
2. [Setup de Alembic para multi-schema](#2-setup-de-alembic)
3. [Workflow de migraciones](#3-workflow-de-migraciones)
4. [Migración inicial — creación de schemas](#4-migración-inicial)
5. [Seed data — entorno de desarrollo](#5-seed-data)
6. [Convenciones de naming](#6-convenciones-de-naming)
7. [Pitfalls comunes y cómo evitarlos](#7-pitfalls)
8. [Comandos de referencia rápida](#8-comandos)

---

## 1. Arquitectura Multi-Schema

La plataforma usa **4 schemas** en PostgreSQL para separar responsabilidades y facilitar el control de permisos a nivel de DB:

| Schema | Propósito | Tablas principales |
|--------|-----------|-------------------|
| `users` | Autenticación y perfiles de usuarios | `accounts`, `profiles`, `roles` |
| `tutor` | Sesiones y mensajes del tutor socrático | `sessions`, `messages`, `prompts` |
| `ctr` | Continuous Tracking Record (hash chain) | `events`, `chains` |
| `analytics` | Métricas de aprendizaje y ejercicios | `student_metrics`, `exercise_attempts`, `course_stats` |

**Por qué múltiples schemas**:
- Separación de responsabilidades clara a nivel de DB
- Permite dar permisos granulares: un rol de reporting puede leer `analytics` sin acceder a `users`
- Facilita la documentación académica: cada schema es un dominio conceptual de la tesis
- Permite un futuro split en microservicios con mínimo refactor (cada schema → su propia DB)

### 1.1 Estructura completa de schemas

```
ainative (database)
├── users (schema)
│   ├── accounts          id, email, password_hash, role, is_active, created_at
│   └── profiles          user_id (FK), full_name, avatar_url, bio, updated_at
│
├── tutor (schema)
│   ├── sessions          id, user_id, exercise_id, started_at, ended_at, status
│   ├── messages          id, session_id, role (user/assistant), content, token_count, created_at
│   └── prompts           id, version_hash (SHA-256), content, created_at, is_active
│
├── ctr (schema)
│   ├── chains            id, session_id, created_at (una chain por sesión)
│   └── events            id, chain_id, sequence_num, event_type, payload (JSONB),
│                         previous_hash, hash (SHA-256), timestamp, user_id
│
└── analytics (schema)
    ├── exercise_attempts  id, user_id, exercise_id, session_id, code_submitted,
    │                      passed, error_type, attempt_num, time_spent_ms, created_at
    ├── student_metrics    user_id (PK), total_sessions, total_messages,
    │                      avg_attempts_per_exercise, last_active, updated_at
    └── course_stats       course_id (PK), total_students, avg_completion_rate,
                           updated_at
```

---

## 2. Setup de Alembic para Multi-Schema

### 2.1 Instalación y configuración inicial

```bash
# En el directorio backend/
pip install alembic

# Inicializar (si no está ya inicializado)
alembic init alembic

# Esto crea:
# alembic/
# ├── env.py             ← configuración principal (MODIFICAR)
# ├── script.py.mako     ← template para migraciones (mantener default)
# └── versions/          ← migraciones generadas aquí
# alembic.ini            ← archivo de configuración (en raíz de backend/)
```

### 2.2 `alembic.ini`

```ini
# alembic.ini
[alembic]
# URL de conexión — puede sobreriderse con la env var ALEMBIC_DATABASE_URL
# NOTA: alembic usa el driver SÍNCRONO (psycopg2/psycopg), no asyncpg
# La app usa asyncpg, pero alembic necesita conexión síncrona
script_location = alembic
sqlalchemy.url = postgresql+psycopg2://postgres:postgres@db:5432/ainative

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

**Nota importante**: Alembic necesita un driver **síncrono** para las migraciones. La app usa `asyncpg` (async) pero Alembic debe usar `psycopg2` o `psycopg` (sync). Por eso el `sqlalchemy.url` usa `postgresql+psycopg2://...`.

Agregar `psycopg2-binary` a las dependencias de desarrollo:
```toml
# pyproject.toml [project.optional-dependencies] → dev
"psycopg2-binary>=2.9.9",
```

### 2.3 `alembic/env.py` — Configuración crítica para multi-schema

```python
# alembic/env.py
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context

# Importar todos los modelos para que Alembic los detecte
# CRÍTICO: si no se importan los modelos, autogenerate no los ve
from app.models.base import Base
from app.models import users, tutor, ctr, analytics  # noqa: F401

config = context.config

# Sobreescribir URL desde env var si está disponible
# Útil para CI/CD donde la URL viene del entorno
database_url = os.environ.get("ALEMBIC_DATABASE_URL") or config.get_main_option("sqlalchemy.url")
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Schemas que Alembic debe incluir en autogenerate
SCHEMAS = ["users", "tutor", "ctr", "analytics"]


def include_object(object, name, type_, reflected, compare_to):
    """
    Filtro para autogenerate: incluir solo tablas de nuestros schemas.
    Excluye tablas del sistema de PostgreSQL.
    """
    if type_ == "table":
        return object.schema in SCHEMAS
    return True


def run_migrations_offline() -> None:
    """Modo offline: genera SQL sin conectarse a la DB."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,
        version_table_schema="public",  # tabla alembic_version en schema public
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo online: conecta a la DB y aplica migraciones."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # sin pool para migraciones (cada run = conexión fresca)
    )

    with connectable.connect() as connection:
        # Crear schemas si no existen (idempotente)
        for schema in SCHEMAS:
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
            version_table_schema="public",
            compare_type=True,       # detecta cambios de tipo de columna
            compare_server_default=True,  # detecta cambios en defaults
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 2.4 Modelos SQLAlchemy con schema explícito

```python
# app/models/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass


# app/models/users.py
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import Base
from enum import Enum
import uuid

class UserRole(str, Enum):
    ALUMNO = "alumno"
    DOCENTE = "docente"
    ADMIN = "admin"

class UserAccount(Base):
    __tablename__ = "accounts"
    __table_args__ = {"schema": "users"}  # ← CRÍTICO: schema explícito

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(72), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, schema="users"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

---

## 3. Workflow de Migraciones

### 3.1 Flujo estándar

```
1. Modificar el modelo SQLAlchemy en app/models/
   ↓
2. Generar migración con autogenerate
   alembic revision --autogenerate -m "descripción"
   ↓
3. REVISAR el archivo generado en alembic/versions/
   ← SIEMPRE revisar antes de aplicar
   ↓
4. Aplicar la migración
   alembic upgrade head
   ↓
5. Verificar en la DB que los cambios son correctos
   docker compose exec db psql -U postgres ainative -c "\d users.accounts"
```

### 3.2 Cuándo revisar obligatoriamente

Siempre revisar, pero con especial atención cuando:
- Se agregan enums (Alembic genera SQL de DROP/CREATE del tipo, lo que puede fallar con datos existentes)
- Se agrega una columna NOT NULL sin default (fallará en tablas con datos)
- Se cambia el tipo de una columna (puede requerir CAST manual)
- Se modifican defaults de columnas JSONB
- Se agregan índices en tablas grandes (en prod: CONCURRENTLY)

### 3.3 Revisión del SQL generado

```bash
# Ver el SQL que se ejecutaría sin aplicarlo:
alembic upgrade head --sql

# Ver el SQL de un rango específico:
alembic upgrade abc123:def456 --sql
```

---

## 4. Migración Inicial — Creación de Schemas

La primera migración crea los 4 schemas y todas las tablas base. Es el punto de partida del sistema.

```python
# alembic/versions/001_initial_schema.py
"""Initial schema creation

Revision ID: 001_initial
Revises:
Create Date: 2026-04-10 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────
    # Crear schemas
    # ──────────────────────────────────────────
    op.execute("CREATE SCHEMA IF NOT EXISTS users")
    op.execute("CREATE SCHEMA IF NOT EXISTS tutor")
    op.execute("CREATE SCHEMA IF NOT EXISTS ctr")
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    # ──────────────────────────────────────────
    # Crear tipos ENUM en sus schemas
    # ──────────────────────────────────────────
    user_role_enum = postgresql.ENUM(
        "alumno", "docente", "admin",
        name="userrole",
        schema="users",
    )
    user_role_enum.create(op.get_bind(), checkfirst=True)

    message_role_enum = postgresql.ENUM(
        "user", "assistant", "system",
        name="messagerole",
        schema="tutor",
    )
    message_role_enum.create(op.get_bind(), checkfirst=True)

    # ──────────────────────────────────────────
    # Schema: users
    # ──────────────────────────────────────────
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(72), nullable=False),
        sa.Column("role", sa.Enum("alumno", "docente", "admin", name="userrole", schema="users"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.text("NOW()")),
        sa.UniqueConstraint("email"),
        schema="users",
    )
    op.create_index("ix_users_accounts_email", "accounts", ["email"], schema="users")

    op.create_table(
        "profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.accounts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        schema="users",
    )

    # ──────────────────────────────────────────
    # Schema: tutor
    # ──────────────────────────────────────────
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exercise_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        schema="tutor",
    )
    op.create_index("ix_tutor_sessions_user_id", "sessions", ["user_id"], schema="tutor")

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tutor.sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Enum("user", "assistant", "system", name="messagerole", schema="tutor"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("prompt_version_hash", sa.String(64), nullable=True),  # SHA-256 del prompt
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        schema="tutor",
    )
    op.create_index("ix_tutor_messages_session_id", "messages", ["session_id"], schema="tutor")

    # ──────────────────────────────────────────
    # Schema: ctr
    # ──────────────────────────────────────────
    op.create_table(
        "chains",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tutor.sessions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        schema="ctr",
    )

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chain_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ctr.chains.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sequence_num", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("previous_hash", sa.String(64), nullable=True),   # NULL para el primer evento
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.UniqueConstraint("chain_id", "sequence_num"),
        schema="ctr",
    )

    # ──────────────────────────────────────────
    # Schema: analytics
    # ──────────────────────────────────────────
    op.create_table(
        "exercise_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exercise_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tutor.sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("code_submitted", sa.Text(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("error_type", sa.String(100), nullable=True),
        sa.Column("attempt_num", sa.Integer(), nullable=False),
        sa.Column("time_spent_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        schema="analytics",
    )
    op.create_index("ix_analytics_attempts_user_exercise", "exercise_attempts", ["user_id", "exercise_id"], schema="analytics")


def downgrade() -> None:
    # Eliminar en orden inverso (FK constraints)
    op.drop_table("exercise_attempts", schema="analytics")
    op.drop_table("events", schema="ctr")
    op.drop_table("chains", schema="ctr")
    op.drop_table("messages", schema="tutor")
    op.drop_table("sessions", schema="tutor")
    op.drop_table("profiles", schema="users")
    op.drop_table("accounts", schema="users")

    # Eliminar ENUMs
    op.execute("DROP TYPE IF EXISTS tutor.messagerole")
    op.execute("DROP TYPE IF EXISTS users.userrole")

    # Eliminar schemas
    op.execute("DROP SCHEMA IF EXISTS analytics")
    op.execute("DROP SCHEMA IF EXISTS ctr")
    op.execute("DROP SCHEMA IF EXISTS tutor")
    op.execute("DROP SCHEMA IF EXISTS users")
```

---

## 5. Seed Data — Entorno de Desarrollo

El script de seed crea datos de prueba de forma **idempotente** (se puede ejecutar múltiples veces sin duplicar datos).

```python
# backend/scripts/seed.py
"""
Script de seed para desarrollo.
Idempotente: usa INSERT ... ON CONFLICT DO NOTHING.

Uso:
    docker compose exec api python scripts/seed.py
"""
import asyncio
import uuid
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import os

DATABASE_URL = os.environ["DATABASE_URL"]

SEED_USERS = [
    {
        "id": "11111111-0000-0000-0000-000000000001",
        "email": "alumno1@test.com",
        "password": "Test1234!",
        "role": "alumno",
        "full_name": "Juan Alumno",
    },
    {
        "id": "11111111-0000-0000-0000-000000000002",
        "email": "docente1@test.com",
        "password": "Test1234!",
        "role": "docente",
        "full_name": "María Docente",
    },
    {
        "id": "11111111-0000-0000-0000-000000000003",
        "email": "admin@test.com",
        "password": "Test1234!",
        "role": "admin",
        "full_name": "Admin Sistema",
    },
]


async def seed():
    engine = create_async_engine(DATABASE_URL)

    async with AsyncSession(engine) as session:
        for user_data in SEED_USERS:
            password_hash = bcrypt.hashpw(
                user_data["password"].encode(), bcrypt.gensalt(rounds=12)
            ).decode()

            # INSERT ... ON CONFLICT DO NOTHING → idempotente
            await session.execute(
                text("""
                    INSERT INTO users.accounts (id, email, password_hash, role)
                    VALUES (:id, :email, :password_hash, :role::users.userrole)
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": user_data["id"],
                    "email": user_data["email"],
                    "password_hash": password_hash,
                    "role": user_data["role"],
                }
            )

            await session.execute(
                text("""
                    INSERT INTO users.profiles (user_id, full_name)
                    VALUES (:user_id, :full_name)
                    ON CONFLICT (user_id) DO NOTHING
                """),
                {"user_id": user_data["id"], "full_name": user_data["full_name"]}
            )

        await session.commit()
        print(f"Seed completado: {len(SEED_USERS)} usuarios creados/verificados")


if __name__ == "__main__":
    asyncio.run(seed())
```

---

## 6. Convenciones de Naming

### 6.1 Archivos de migración

```
{id}_{descripción_breve}.py

Ejemplos:
001_initial_schema.py           ← Migración inicial
002_add_exercise_table.py       ← Nueva tabla
003_add_idx_sessions_user.py    ← Nuevo índice
004_alter_messages_add_column.py ← Columna nueva
005_fix_ctr_hash_null.py        ← Hotfix
```

Alembic genera IDs aleatorios (hash corto). Renombrarlos opcionalmente con números secuenciales para claridad en proyectos pequeños.

### 6.2 Objetos de DB

| Objeto | Convención | Ejemplo |
|--------|-----------|---------|
| Tablas | `snake_case`, plural | `exercise_attempts` |
| Columnas | `snake_case` | `password_hash` |
| Índices | `ix_{schema}_{tabla}_{columnas}` | `ix_users_accounts_email` |
| FKs | `fk_{tabla}_{columna}_{ref_tabla}` | `fk_sessions_user_id_accounts` |
| ENUMs | `{nombre}` en el schema correspondiente | `userrole` en `users` |
| Constraints unique | `uq_{tabla}_{columnas}` | `uq_accounts_email` |

---

## 7. Pitfalls Comunes

### P1: Falta el prefijo de schema en ForeignKey

```python
# INCORRECTO — Alembic no sabe en qué schema buscar "accounts"
sa.ForeignKey("accounts.id")

# CORRECTO — siempre incluir schema.tabla
sa.ForeignKey("users.accounts.id")
```

### P2: JSONB con default mutable

```python
# INCORRECTO — Python evalúa {} una sola vez para todas las filas
sa.Column("metadata", postgresql.JSONB(), default={})

# CORRECTO — usar server_default para que PostgreSQL genere el default
sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"))
```

### P3: Migraciones de ENUMs con datos existentes

Cuando se **agrega** un valor a un ENUM existente:
```python
# Alembic autogenera DROP TYPE / CREATE TYPE — PELIGROSO si hay datos

# En su lugar, usar ALTER TYPE ADD VALUE (no requiere drop):
def upgrade():
    op.execute("ALTER TYPE users.userrole ADD VALUE IF NOT EXISTS 'superadmin'")

def downgrade():
    # No se puede remover un valor de enum en PostgreSQL sin recrearlo
    # Requiere: CREATE TYPE nuevo, ALTER TABLE, DROP TYPE viejo
    raise NotImplementedError("No se puede revertir ADD VALUE en enum PostgreSQL")
```

### P4: Columna NOT NULL sin default en tabla con datos

```python
# Si la tabla ya tiene filas, esto fallará:
op.add_column("accounts", sa.Column("phone", sa.String(20), nullable=False), schema="users")

# Correcto: agregar como nullable primero, luego hacer NOT NULL con ALTER
def upgrade():
    # 1. Agregar nullable
    op.add_column("accounts", sa.Column("phone", sa.String(20), nullable=True), schema="users")
    # 2. Poblar datos existentes
    op.execute("UPDATE users.accounts SET phone = '' WHERE phone IS NULL")
    # 3. Hacer NOT NULL
    op.alter_column("accounts", "phone", nullable=False, schema="users")
```

### P5: Índices en tablas grandes (producción)

```python
# Bloquea la tabla durante la creación — NO usar en producción con datos
op.create_index("ix_ctr_events_user_id", "events", ["user_id"], schema="ctr")

# En producción usar CONCURRENTLY (no bloquea la tabla):
def upgrade():
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ctr_events_user_id ON ctr.events (user_id)")

def downgrade():
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_ctr_events_user_id")
```

### P6: Olvidar revisar el SQL generado

Alembic autogenerate es útil pero no infalible. Siempre revisar con `--sql` antes de aplicar en staging o producción. Los errores más comunes de autogenerate:
- Detecta como "nueva tabla" tablas que existen pero en otro schema
- Genera DROP/CREATE para cambios de ENUM cuando debería ser ALTER
- No detecta algunos cambios de CHECK constraints
- Puede generar índices duplicados si hay reflexión del schema activa

---

## 8. Comandos de Referencia Rápida

```bash
# ──────────────────────────────────────────
# Generar y aplicar
# ──────────────────────────────────────────

# Generar migración desde cambios en modelos
alembic revision --autogenerate -m "descripción breve"

# Aplicar todas las migraciones pendientes
alembic upgrade head

# Aplicar hasta una revisión específica
alembic upgrade 003_add_exercise_table

# Aplicar N migraciones más
alembic upgrade +2

# ──────────────────────────────────────────
# Inspección
# ──────────────────────────────────────────

# Ver estado actual
alembic current

# Ver historial de migraciones
alembic history --verbose

# Ver SQL que se ejecutaría
alembic upgrade head --sql

# ──────────────────────────────────────────
# Rollback
# ──────────────────────────────────────────

# Revertir la última migración
alembic downgrade -1

# Revertir N migraciones
alembic downgrade -3

# Revertir hasta una revisión específica
alembic downgrade 001_initial_schema

# Revertir todo (base = sin migraciones)
alembic downgrade base

# ──────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────

# Crear migración vacía para escribir manualmente
alembic revision -m "custom_migration"

# Marcar una revisión como aplicada sin ejecutarla (sync manual)
alembic stamp head

# Verificar que los modelos están sincronizados con la DB
alembic check
```

---

**Referencias internas**:
- `knowledge-base/02-arquitectura/02_modelo_de_datos.md` — definición completa de tablas
- `knowledge-base/04-infraestructura/01_configuracion.md` — DATABASE_URL y configuración
- `knowledge-base/04-infraestructura/03_deploy.md` — ejecución de migraciones en startup
