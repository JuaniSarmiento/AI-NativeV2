from __future__ import annotations

import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from hashlib import sha256

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.shared.models.activity import Activity, ActivityStatus
from app.shared.models.llm_config import LLMConfig, LLMProvider


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = sha256(settings.secret_key.encode()).digest()
    fernet_key = urlsafe_b64encode(key)
    return Fernet(fernet_key)


class LLMConfigService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: uuid.UUID) -> LLMConfig | None:
        result = await self._session.execute(
            select(LLMConfig).where(LLMConfig.user_id == user_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def save(
        self,
        user_id: uuid.UUID,
        provider: LLMProvider,
        api_key: str,
        model_name: str,
    ) -> LLMConfig:
        fernet = _get_fernet()
        encrypted_key = fernet.encrypt(api_key.encode()).decode()

        existing = await self.get(user_id)
        if existing:
            existing.provider = provider
            existing.api_key_encrypted = encrypted_key
            existing.model_name = model_name
            await self._session.flush()
            return existing

        config = LLMConfig(
            user_id=user_id,
            provider=provider,
            api_key_encrypted=encrypted_key,
            model_name=model_name,
        )
        self._session.add(config)
        await self._session.flush()
        return config

    def decrypt_key(self, config: LLMConfig) -> str:
        fernet = _get_fernet()
        return fernet.decrypt(config.api_key_encrypted.encode()).decode()


class ActivityService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        course_id: uuid.UUID,
        created_by: uuid.UUID,
        title: str,
        description: str | None,
        prompt_used: str | None,
    ) -> Activity:
        activity = Activity(
            course_id=course_id,
            created_by=created_by,
            title=title,
            description=description,
            prompt_used=prompt_used,
            status=ActivityStatus.draft,
        )
        self._session.add(activity)
        await self._session.flush()
        return activity

    async def get(self, activity_id: uuid.UUID) -> Activity:
        result = await self._session.execute(
            select(Activity)
            .where(Activity.id == activity_id, Activity.is_active.is_(True))
            .options(selectinload(Activity.exercises))
        )
        activity = result.scalar_one_or_none()
        if activity is None:
            raise NotFoundError(resource="Activity", identifier=str(activity_id))
        return activity

    async def list_by_user(
        self, user_id: uuid.UUID, page: int = 1, per_page: int = 20
    ) -> tuple[list[Activity], int]:
        from sqlalchemy import func

        base = select(Activity).where(
            Activity.created_by == user_id, Activity.is_active.is_(True)
        )
        count = (await self._session.execute(
            select(func.count()).select_from(base.subquery())
        )).scalar_one()

        items = (await self._session.execute(
            base.offset((page - 1) * per_page).limit(per_page).order_by(Activity.created_at.desc())
        )).scalars().all()

        return list(items), count

    async def update(self, activity_id: uuid.UUID, data: dict) -> Activity:
        activity = await self.get(activity_id)
        for key, value in data.items():
            if value is not None:
                setattr(activity, key, value)
        await self._session.flush()
        return activity

    async def publish(self, activity_id: uuid.UUID) -> Activity:
        activity = await self.get(activity_id)
        if activity.status == ActivityStatus.published:
            raise ValidationError(message="Activity is already published.")

        activity.status = ActivityStatus.published
        for exercise in activity.exercises:
            exercise.is_active = True

        await self._session.flush()
        return activity

    async def delete(self, activity_id: uuid.UUID) -> Activity:
        activity = await self.get(activity_id)
        activity.is_active = False
        for exercise in activity.exercises:
            exercise.is_active = False
        await self._session.flush()
        return activity
