"""Base seed data: users (admin, docente, alumno), 1 course, 1 commission.

Idempotent — checks for existing records by email/name before inserting.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def seed(session: AsyncSession) -> None:
    from app.shared.models.user import User, UserRole
    from app.shared.models.course import Course
    from app.shared.models.commission import Commission

    # ---- Users ----
    existing_user = await session.execute(
        select(User).where(User.email == "admin@ainative.dev").limit(1)
    )
    if existing_user.scalar_one_or_none():
        logger.info("Base users already seeded — skipping.")
    else:
        # Pre-computed bcrypt hash of "test1234" for dev seeds.
        _HASH = "$2b$12$WzD5ZpOk02EInTeAj1iqpeKQJ30PYCArJHfv6o2BmOEW5x/O3MBZy"  # noqa: N806, S105

        admin = User(
            email="admin@ainative.dev",
            password_hash=_HASH,
            full_name="Administrador del Sistema",
            role=UserRole.admin,
        )
        docente = User(
            email="docente@ainative.dev",
            password_hash=_HASH,
            full_name="Prof. Roberto Sánchez",
            role=UserRole.docente,
        )
        alumno = User(
            email="alumno@ainative.dev",
            password_hash=_HASH,
            full_name="Ana García",
            role=UserRole.alumno,
        )
        session.add_all([admin, docente, alumno])
        await session.flush()
        logger.info("Seeded 3 users: admin, docente, alumno.")

    # ---- Course ----
    existing_course = await session.execute(
        select(Course).where(Course.name == "Programación I").limit(1)
    )
    course = existing_course.scalar_one_or_none()
    if course:
        logger.info("Base course already seeded — skipping.")
    else:
        course = Course(
            name="Programación I",
            description="Introducción a la programación estructurada con Python.",
            topic_taxonomy={
                "name": "Programación I",
                "children": [
                    {"name": "Variables y Tipos", "children": []},
                    {"name": "Control de Flujo", "children": [
                        {"name": "Condicionales", "children": []},
                        {"name": "Bucles", "children": []},
                    ]},
                    {"name": "Funciones", "children": []},
                    {"name": "Listas y Diccionarios", "children": []},
                ],
            },
        )
        session.add(course)
        await session.flush()
        logger.info("Seeded 1 course: Programación I.")

    # ---- Commission ----
    existing_commission = await session.execute(
        select(Commission).where(Commission.name == "K1001").limit(1)
    )
    if existing_commission.scalar_one_or_none():
        logger.info("Base commission already seeded — skipping.")
    else:
        # Get the docente user for teacher_id
        docente_result = await session.execute(
            select(User).where(User.email == "docente@ainative.dev").limit(1)
        )
        docente_user = docente_result.scalar_one()

        commission = Commission(
            course_id=course.id,
            teacher_id=docente_user.id,
            name="K1001",
            year=2026,
            semester=1,
        )
        session.add(commission)
        await session.flush()
        logger.info("Seeded 1 commission: K1001.")
