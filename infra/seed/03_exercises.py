"""Seed exercises for Programacion I."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def seed(session: AsyncSession) -> None:
    from app.shared.models.course import Course
    from app.shared.models.exercise import Exercise

    existing = await session.execute(
        select(Exercise).limit(1)
    )
    if existing.scalar_one_or_none():
        logger.info("Exercises already seeded — skipping.")
        return

    course_result = await session.execute(
        select(Course).where(Course.name == "Programacion I").limit(1)
    )
    course = course_result.scalar_one_or_none()
    if not course:
        # Try original name from seed 01
        course_result = await session.execute(
            select(Course).limit(1)
        )
        course = course_result.scalar_one_or_none()
    if not course:
        logger.warning("No course found — skipping exercise seed.")
        return

    exercises = [
        Exercise(
            course_id=course.id,
            title="Hola Mundo y tipos de datos",
            description=(
                "Escribi un programa que solicite el nombre del usuario "
                "y lo salude mostrando su nombre en mayusculas.\n\n"
                "**Ejemplo:**\n"
                "- Entrada: `maria`\n"
                "- Salida: `Hola, MARIA!`"
            ),
            test_cases={
                "language": "python",
                "timeout_ms": 10000,
                "memory_limit_mb": 128,
                "cases": [
                    {
                        "id": "tc-001",
                        "description": "Nombre simple",
                        "input": "maria",
                        "expected_output": "Hola, MARIA!",
                        "is_hidden": False,
                        "weight": 1.0,
                    },
                    {
                        "id": "tc-002",
                        "description": "Nombre con espacios",
                        "input": "juan pablo",
                        "expected_output": "Hola, JUAN PABLO!",
                        "is_hidden": True,
                        "weight": 1.0,
                    },
                ],
            },
            difficulty="easy",
            topic_tags=["variables", "strings", "input-output"],
            starter_code='nombre = input("Ingresa tu nombre: ")\n# Tu codigo aca\n',
            order_index=1,
        ),
        Exercise(
            course_id=course.id,
            title="Calculadora basica",
            description=(
                "Implementa una calculadora que acepte dos numeros y un operador "
                "(+, -, *, /) y devuelva el resultado. Maneja division por cero."
            ),
            test_cases={
                "language": "python",
                "timeout_ms": 10000,
                "memory_limit_mb": 128,
                "cases": [
                    {
                        "id": "tc-001",
                        "description": "Suma",
                        "input": "5\n3\n+",
                        "expected_output": "8.0",
                        "is_hidden": False,
                        "weight": 1.0,
                    },
                    {
                        "id": "tc-002",
                        "description": "Division por cero",
                        "input": "10\n0\n/",
                        "expected_output": "Error: division por cero",
                        "is_hidden": False,
                        "weight": 1.0,
                    },
                ],
            },
            difficulty="medium",
            topic_tags=["operadores", "condicionales", "manejo-errores"],
            starter_code="# Lee dos numeros y un operador\n",
            order_index=2,
        ),
        Exercise(
            course_id=course.id,
            title="FizzBuzz",
            description=(
                "Para numeros del 1 al 100: imprime 'Fizz' si es multiplo de 3, "
                "'Buzz' si es multiplo de 5, 'FizzBuzz' si es multiplo de ambos, "
                "o el numero si no cumple ninguna condicion."
            ),
            test_cases={
                "language": "python",
                "timeout_ms": 10000,
                "memory_limit_mb": 128,
                "cases": [
                    {
                        "id": "tc-001",
                        "description": "Primeros 15 valores",
                        "input": "",
                        "expected_output": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz",
                        "is_hidden": False,
                        "weight": 1.0,
                    },
                ],
            },
            difficulty="hard",
            topic_tags=["bucles", "condicionales", "logica"],
            starter_code="# Imprime FizzBuzz del 1 al 100\n",
            order_index=3,
        ),
    ]

    session.add_all(exercises)
    await session.flush()
    logger.info("Seeded 3 exercises for %s.", course.name)
