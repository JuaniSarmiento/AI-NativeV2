from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, MappedColumn

# Naming convention for Alembic autogenerate — avoids anonymous constraint names
# that make migration rollbacks impossible.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy models.

    Every model in every schema must inherit from this single Base so that
    ``Base.metadata`` contains the full graph and Alembic can diff it in one pass.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    type_annotation_map = {
        uuid.UUID: PG_UUID(as_uuid=True),
        datetime: "TIMESTAMP WITH TIME ZONE",
    }
