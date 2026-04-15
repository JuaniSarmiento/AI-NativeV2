from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register_and_login(
    client: AsyncClient,
    email: str,
    role: str = "docente",
) -> str:
    """Helper: register + login, return access token."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "full_name": f"Test {role.title()}",
            "role": role,
        },
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    return res.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_create_course_as_docente(client: AsyncClient) -> None:
    token = await _register_and_login(client, "doc-courses@test.dev", "docente")
    res = await client.post(
        "/api/v1/courses",
        json={"name": "Algoritmos I", "description": "Primer curso de algoritmos"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "ok"
    assert body["data"]["name"] == "Algoritmos I"


@pytest.mark.asyncio
async def test_alumno_cannot_create_course(client: AsyncClient) -> None:
    token = await _register_and_login(client, "alu-courses@test.dev", "alumno")
    res = await client.post(
        "/api/v1/courses",
        json={"name": "Hack Course"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_list_courses_paginated(client: AsyncClient) -> None:
    token = await _register_and_login(client, "doc-list@test.dev", "docente")

    # Create 3 courses
    for i in range(3):
        await client.post(
            "/api/v1/courses",
            json={"name": f"Curso Paginated {i}"},
            headers={"Authorization": f"Bearer {token}"},
        )

    # List with pagination
    res = await client.get(
        "/api/v1/courses?page=1&per_page=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["data"]) == 2
    assert body["meta"]["total"] >= 3


@pytest.mark.asyncio
async def test_enroll_and_list_student_courses(client: AsyncClient) -> None:
    doc_token = await _register_and_login(client, "doc-enroll@test.dev", "docente")
    alu_token = await _register_and_login(client, "alu-enroll@test.dev", "alumno")

    # Docente creates course + commission
    course_res = await client.post(
        "/api/v1/courses",
        json={"name": "Curso Enroll Test"},
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    course_id = course_res.json()["data"]["id"]

    # Get docente user id for teacher_id
    doc_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "doc-enroll@test.dev", "password": "securepass123"},
    )
    doc_user_id = doc_login.json()["data"]["user"]["id"]

    commission_res = await client.post(
        f"/api/v1/courses/{course_id}/commissions",
        json={"name": "K-TEST", "teacher_id": doc_user_id, "year": 2026, "semester": 1},
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    commission_id = commission_res.json()["data"]["id"]

    # Alumno enrolls
    enroll_res = await client.post(
        f"/api/v1/commissions/{commission_id}/enroll",
        headers={"Authorization": f"Bearer {alu_token}"},
    )
    assert enroll_res.status_code == 201

    # Alumno lists their courses
    my_courses = await client.get(
        "/api/v1/student/courses",
        headers={"Authorization": f"Bearer {alu_token}"},
    )
    assert my_courses.status_code == 200
    data = my_courses.json()["data"]
    assert len(data) >= 1
    assert any(c["commission_name"] == "K-TEST" for c in data)


@pytest.mark.asyncio
async def test_duplicate_enrollment_rejected(client: AsyncClient) -> None:
    doc_token = await _register_and_login(client, "doc-dupe@test.dev", "docente")
    alu_token = await _register_and_login(client, "alu-dupe@test.dev", "alumno")

    course_res = await client.post(
        "/api/v1/courses",
        json={"name": "Curso Dupe Test"},
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    course_id = course_res.json()["data"]["id"]

    doc_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "doc-dupe@test.dev", "password": "securepass123"},
    )
    doc_user_id = doc_login.json()["data"]["user"]["id"]

    comm_res = await client.post(
        f"/api/v1/courses/{course_id}/commissions",
        json={"name": "K-DUPE", "teacher_id": doc_user_id, "year": 2026, "semester": 1},
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    commission_id = comm_res.json()["data"]["id"]

    # First enrollment
    res1 = await client.post(
        f"/api/v1/commissions/{commission_id}/enroll",
        headers={"Authorization": f"Bearer {alu_token}"},
    )
    assert res1.status_code == 201

    # Duplicate enrollment
    res2 = await client.post(
        f"/api/v1/commissions/{commission_id}/enroll",
        headers={"Authorization": f"Bearer {alu_token}"},
    )
    assert res2.status_code == 409
