from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db.base import Base


class LLMProvider(str, enum.Enum):
    openai = "openai"
    anthropic = "anthropic"
    mistral = "mistral"
    gemini = "gemini"


class LLMConfig(Base):
    """Per-docente LLM API key configuration.

    The api_key_encrypted field stores the Fernet-encrypted API key.
    It is NEVER returned in plaintext to the frontend.

    Schema: operational.
    """

    __tablename__ = "llm_configs"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_llm_configs_user_id"),
        {"schema": "operational"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("operational.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[LLMProvider] = mapped_column(
        Enum(LLMProvider, name="llm_provider", schema="operational"),
        nullable=False,
    )
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="gpt-4o-mini",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(),
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<LLMConfig user={self.user_id} provider={self.provider.value}>"
