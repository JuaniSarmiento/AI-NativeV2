from __future__ import annotations

import pytest
from httpx import AsyncClient

VALID_TEST_CASES = {
    "language": "python",
    "timeout_ms": 10000,
    "memory_limit_mb": 128,
    "cases": [
        {
            "id": "tc-001",
            "description": "Basic test",
            "input": "hello",
            "expected_output": "HELLO",
            "is_hidden": False,
            "weight": 1.0,
        }
    ],
}


async def _setup_docente(client: AsyncClient) -> tuple[str, str]:
    """Register docente, login, create course, return (token, course_id)."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "doc-ex@test.dev", "password": "securepass123", "full_name": "Doc Ex", "role": "docente"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "doc-ex@test.dev", "password": "securepass123"},
    )
    token = login.json()["data"]["access_token"]

    course = await client.post(
        "/api/v1/courses",
        json={"name": "Curso Ejercicios Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    course_id = course.json()["data"]["id"]
    return token, course_id


@pytest.mark.asyncio
async def test_create_exercise(client: AsyncClient) -> None:
    token, course_id = await _setup_docente(client)

    res = await client.post(
        f"/api/v1/courses/{course_id}/exercises",
        json={
            "title": "Test Exercise",
            "description": "Write a function...",
            "test_cases": VALID_TEST_CASES,
            "difficulty": "easy",
            "topic_tags": ["strings"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["data"]["title"] == "Test Exercise"
    assert body["data"]["difficulty"] == "easy"
    assert len(body["data"]["test_cases"]["cases"]) == 1


@pytest.mark.asyncio
async def test_alumno_cannot_create_exercise(client: AsyncClient) -> None:
    _, course_id = await _setup_docente(client)

    await client.post(
        "/api/v1/auth/register",
        json={"email": "alu-ex@test.dev", "password": "securepass123", "full_name": "Alu Ex", "role": "alumno"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "alu-ex@test.dev", "password": "securepass123"},
    )
    alu_token = login.json()["data"]["access_token"]

    res = await client.post(
        f"/api/v1/courses/{course_id}/exercises",
        json={
            "title": "Hack Exercise",
            "description": "Nope",
            "test_cases": VALID_TEST_CASES,
            "difficulty": "easy",
        },
        headers={"Authorization": f"Bearer {alu_token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_reads_problem_event_on_student_access(client: AsyncClient) -> None:
    token, course_id = await _setup_docente(client)

    # Create exercise
    ex_res = await client.post(
        f"/api/v1/courses/{course_id}/exercises",
        json={
            "title": "Event Test Exercise",
            "description": "Triggers reads_problem",
            "test_cases": VALID_TEST_CASES,
            "difficulty": "medium",
            "topic_tags": ["events"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    exercise_id = ex_res.json()["data"]["id"]

    # Register alumno + get token
    await client.post(
        "/api/v1/auth/register",
        json={"email": "alu-event@test.dev", "password": "securepass123", "full_name": "Alu Event", "role": "alumno"},
    )
    alu_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "alu-event@test.dev", "password": "securepass123"},
    )
    alu_token = alu_login.json()["data"]["access_token"]

    # Access exercise detail as alumno — should emit reads_problem
    detail_res = await client.get(
        f"/api/v1/exercises/{exercise_id}",
        headers={"Authorization": f"Bearer {alu_token}"},
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["title"] == "Event Test Exercise"


@pytest.mark.asyncio
async def test_invalid_test_cases_rejected(client: AsyncClient) -> None:
    token, course_id = await _setup_docente(client)

    res = await client.post(
        f"/api/v1/courses/{course_id}/exercises",
        json={
            "title": "Bad Test Cases",
            "description": "Should fail",
            "test_cases": {"language": "python", "cases": []},
            "difficulty": "easy",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422
