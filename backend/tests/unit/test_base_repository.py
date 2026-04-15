"""Tests for BaseRepository generic CRUD operations.

Uses the Course model as the test subject since it has simple fields
and an is_active flag for soft delete testing.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.shared.models.course import Course
from app.shared.models.commission import Commission
from app.shared.models.user import User, UserRole
from app.shared.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Course)


@pytest.mark.asyncio
async def test_create(db_session: AsyncSession) -> None:
    repo = CourseRepository(db_session)
    course = await repo.create({"name": "Test Course", "description": "A test"})

    assert course.id is not None
    assert course.name == "Test Course"
    assert course.is_active is True


@pytest.mark.asyncio
async def test_get_by_id(db_session: AsyncSession) -> None:
    repo = CourseRepository(db_session)
    created = await repo.create({"name": "Findable Course"})

    found = await repo.get_by_id(created.id)
    assert found.id == created.id
    assert found.name == "Findable Course"


@pytest.mark.asyncio
async def test_get_by_id_not_found(db_session: AsyncSession) -> None:
    repo = CourseRepository(db_session)
    fake_id = uuid.uuid4()

    with pytest.raises(NotFoundError) as exc_info:
        await repo.get_by_id(fake_id)

    assert "Course" in exc_info.value.message
    assert str(fake_id) in exc_info.value.message


@pytest.mark.asyncio
async def test_get_by_id_excludes_inactive(db_session: AsyncSession) -> None:
    repo = CourseRepository(db_session)
    created = await repo.create({"name": "Inactive Course", "is_active": False})

    with pytest.raises(NotFoundError):
        await repo.get_by_id(created.id)

    # But with include_inactive=True it should work
    found = await repo.get_by_id(created.id, include_inactive=True)
    assert found.id == created.id


@pytest.mark.asyncio
async def test_list_paginated(db_session: AsyncSession) -> None:
    repo = CourseRepository(db_session)
    for i in range(5):
        await repo.create({"name": f"Course {i}"})

    items, total = await repo.list(page=1, per_page=3)
    assert len(items) == 3
    assert total == 5

    items2, total2 = await repo.list(page=2, per_page=3)
    assert len(items2) == 2
    assert total2 == 5


@pytest.mark.asyncio
async def test_list_excludes_inactive(db_session: AsyncSession) -> None:
    repo = CourseRepository(db_session)
    await repo.create({"name": "Active"})
    await repo.create({"name": "Inactive", "is_active": False})

    items, total = await repo.list()
    assert total == 1
    assert items[0].name == "Active"

    items_all, total_all = await repo.list(include_inactive=True)
    assert total_all == 2


@pytest.mark.asyncio
async def test_update(db_session: AsyncSession) -> None:
    repo = CourseRepository(db_session)
    created = await repo.create({"name": "Old Name"})

    updated = await repo.update(created.id, {"name": "New Name"})
    assert updated.name == "New Name"
    assert updated.id == created.id


@pytest.mark.asyncio
async def test_soft_delete(db_session: AsyncSession) -> None:
    repo = CourseRepository(db_session)
    created = await repo.create({"name": "To Delete"})
    assert created.is_active is True

    deleted = await repo.soft_delete(created.id)
    assert deleted.is_active is False

    # Should not be findable without include_inactive
    with pytest.raises(NotFoundError):
        await repo.get_by_id(created.id)


@pytest.mark.asyncio
async def test_load_options(db_session: AsyncSession) -> None:
    repo = CourseRepository(db_session)
    course = await repo.create({"name": "Course with Commissions"})

    # Create a teacher first
    teacher = User(
        email="test-teacher@test.dev",
        password_hash="fakehash",
        full_name="Test Teacher",
        role=UserRole.docente,
    )
    db_session.add(teacher)
    await db_session.flush()

    commission = Commission(
        course_id=course.id,
        teacher_id=teacher.id,
        name="K9999",
        year=2026,
        semester=1,
    )
    db_session.add(commission)
    await db_session.flush()

    # Load with selectinload
    loaded = await repo.get_by_id(
        course.id,
        load_options=[selectinload(Course.commissions)],
    )
    assert len(loaded.commissions) == 1
    assert loaded.commissions[0].name == "K9999"
