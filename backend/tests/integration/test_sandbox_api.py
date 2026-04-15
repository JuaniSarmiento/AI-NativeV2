from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _setup_student_with_exercise(client: AsyncClient) -> tuple[str, str]:
    """Register docente + alumno, create course + commission + exercise, enroll student. Return (alu_token, exercise_id)."""
    # Docente
    await client.post("/api/v1/auth/register", json={"email": "doc-sb@test.dev", "password": "securepass123", "full_name": "Doc Sandbox", "role": "docente"})
    doc_login = await client.post("/api/v1/auth/login", json={"email": "doc-sb@test.dev", "password": "securepass123"})
    doc_token = doc_login.json()["data"]["access_token"]
    doc_id = doc_login.json()["data"]["user"]["id"]

    # Course + commission
    course = await client.post("/api/v1/courses", json={"name": "Sandbox Test Course"}, headers={"Authorization": f"Bearer {doc_token}"})
    course_id = course.json()["data"]["id"]
    comm = await client.post(f"/api/v1/courses/{course_id}/commissions", json={"name": "K-SB", "teacher_id": doc_id, "year": 2026, "semester": 1}, headers={"Authorization": f"Bearer {doc_token}"})
    comm_id = comm.json()["data"]["id"]

    # Exercise
    ex = await client.post(f"/api/v1/courses/{course_id}/exercises", json={
        "title": "Sandbox Test Exercise",
        "description": "Add two numbers",
        "test_cases": {
            "language": "python",
            "timeout_ms": 10000,
            "memory_limit_mb": 128,
            "cases": [
                {"id": "tc-001", "description": "Basic", "input": "3\n5", "expected_output": "8", "is_hidden": False, "weight": 1.0},
                {"id": "tc-002", "description": "Zeros", "input": "0\n0", "expected_output": "0", "is_hidden": True, "weight": 1.0},
            ],
        },
        "difficulty": "easy",
        "topic_tags": ["sandbox"],
    }, headers={"Authorization": f"Bearer {doc_token}"})
    exercise_id = ex.json()["data"]["id"]

    # Alumno
    await client.post("/api/v1/auth/register", json={"email": "alu-sb@test.dev", "password": "securepass123", "full_name": "Alu Sandbox", "role": "alumno"})
    alu_login = await client.post("/api/v1/auth/login", json={"email": "alu-sb@test.dev", "password": "securepass123"})
    alu_token = alu_login.json()["data"]["access_token"]

    # Enroll
    await client.post(f"/api/v1/commissions/{comm_id}/enroll", headers={"Authorization": f"Bearer {alu_token}"})

    return alu_token, exercise_id


@pytest.mark.asyncio
async def test_run_code_with_passing_tests(client: AsyncClient) -> None:
    alu_token, exercise_id = await _setup_student_with_exercise(client)

    res = await client.post(
        f"/api/v1/student/exercises/{exercise_id}/run",
        json={"code": "a = int(input())\nb = int(input())\nprint(a + b)", "stdin": "3\n5"},
        headers={"Authorization": f"Bearer {alu_token}"},
    )
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["status"] == "ok"
    assert "8" in body["stdout"]


@pytest.mark.asyncio
async def test_run_code_syntax_error(client: AsyncClient) -> None:
    alu_token, exercise_id = await _setup_student_with_exercise(client)

    res = await client.post(
        f"/api/v1/student/exercises/{exercise_id}/run",
        json={"code": "def broken(\n  pass"},
        headers={"Authorization": f"Bearer {alu_token}"},
    )
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["status"] in ("syntax_error", "error")


@pytest.mark.asyncio
async def test_non_enrolled_student_rejected(client: AsyncClient) -> None:
    _, exercise_id = await _setup_student_with_exercise(client)

    # Register a different student (not enrolled)
    await client.post("/api/v1/auth/register", json={"email": "outsider@test.dev", "password": "securepass123", "full_name": "Outsider", "role": "alumno"})
    login = await client.post("/api/v1/auth/login", json={"email": "outsider@test.dev", "password": "securepass123"})
    outsider_token = login.json()["data"]["access_token"]

    res = await client.post(
        f"/api/v1/student/exercises/{exercise_id}/run",
        json={"code": "print('hack')"},
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert res.status_code == 403
