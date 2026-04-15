"""Extended seed: additional course, commissions, and enrollments.

Depends on 01_base_data.py having created users, 1 course, and 1 commission.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def seed(session: AsyncSession) -> None:
    from app.shared.models.course import Course
    from app.shared.models.commission import Commission
    from app.shared.models.enrollment import Enrollment
    from app.shared.models.user import User

    # Check if already seeded
    existing = await session.execute(
        select(Course).where(Course.name == "Programacion II").limit(1)
    )
    if existing.scalar_one_or_none():
        logger.info("Courses/enrollments already seeded — skipping.")
        return

    # Create second course
    prog2 = Course(
        name="Programacion II",
        description="Programacion orientada a objetos y estructuras de datos con Python.",
        topic_taxonomy={
            "name": "Programacion II",
            "children": [
                {"name": "Clases y Objetos", "children": []},
                {"name": "Herencia y Polimorfismo", "children": []},
                {"name": "Estructuras de Datos", "children": [
                    {"name": "Pilas", "children": []},
                    {"name": "Colas", "children": []},
                    {"name": "Arboles", "children": []},
                ]},
            ],
        },
    )
    session.add(prog2)
    await session.flush()

    # Get existing docente
    docente_result = await session.execute(
        select(User).where(User.email == "docente@ainative.dev").limit(1)
    )
    docente = docente_result.scalar_one()

    # Create commissions for prog2
    k2001 = Commission(
        course_id=prog2.id,
        teacher_id=docente.id,
        name="K2001",
        year=2026,
        semester=1,
    )
    k2002 = Commission(
        course_id=prog2.id,
        teacher_id=docente.id,
        name="K2002",
        year=2026,
        semester=1,
    )
    session.add_all([k2001, k2002])
    await session.flush()

    # Get alumno and existing commission K1001
    alumno_result = await session.execute(
        select(User).where(User.email == "alumno@ainative.dev").limit(1)
    )
    alumno = alumno_result.scalar_one()

    k1001_result = await session.execute(
        select(Commission).where(Commission.name == "K1001").limit(1)
    )
    k1001 = k1001_result.scalar_one()

    # Enroll alumno in K1001 and K2001
    enrollment1 = Enrollment(student_id=alumno.id, commission_id=k1001.id)
    enrollment2 = Enrollment(student_id=alumno.id, commission_id=k2001.id)
    session.add_all([enrollment1, enrollment2])
    await session.flush()

    logger.info("Seeded: 1 course (Programacion II), 2 commissions (K2001, K2002), 2 enrollments.")
