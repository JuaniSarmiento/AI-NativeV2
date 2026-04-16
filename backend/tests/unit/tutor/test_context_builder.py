"""Unit tests for ContextBuilder — mocked DB session."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.features.tutor.context_builder import (
    ContextBuilder,
    _truncate_code,
    _CODE_TRUNCATE_LIMIT,
    _TRUNCATION_PREFIX,
)
from app.core.exceptions import NotFoundError


# ---------------------------------------------------------------------------
# Helpers to build fake domain objects
# ---------------------------------------------------------------------------


def _make_exercise(
    *,
    title: str = "Suma de lista",
    description: str = "Escribí una función que sume los elementos de una lista.",
    difficulty_value: str = "medium",
    topic_tags: list[str] | None = None,
    language: str = "Python",
    starter_code: str = "",
    rubric: str | None = None,
    activity: object | None = None,
    activity_id: uuid.UUID | None = None,
) -> MagicMock:
    ex = MagicMock()
    ex.id = uuid.uuid4()
    ex.title = title
    ex.description = description
    ex.difficulty = MagicMock()
    ex.difficulty.value = difficulty_value
    ex.topic_tags = topic_tags if topic_tags is not None else ["listas", "bucles"]
    ex.language = language
    ex.starter_code = starter_code
    ex.rubric = rubric
    ex.activity = activity
    ex.activity_id = activity_id
    return ex


def _make_snapshot(code: str) -> MagicMock:
    snap = MagicMock()
    snap.code = code
    snap.snapshot_at = datetime.now(tz=timezone.utc)
    return snap


def _make_activity(title: str = "Actividad 1", description: str = "Desc actividad") -> MagicMock:
    act = MagicMock()
    act.title = title
    act.description = description
    return act


# ---------------------------------------------------------------------------
# Minimal prompt template used across tests
# ---------------------------------------------------------------------------

MINIMAL_TEMPLATE = (
    "Ejercicio: {exercise_title}\n"
    "Descripcion: {exercise_description}\n"
    "Dificultad: {exercise_difficulty}\n"
    "Temas: {exercise_topics}\n"
    "Lenguaje: {exercise_language}\n"
    "Codigo:\n{student_code}"
)

TEMPLATE_WITH_RUBRIC = MINIMAL_TEMPLATE + "\n### Rúbrica del ejercicio\n{exercise_rubric}"

TEMPLATE_WITH_ACTIVITY = (
    MINIMAL_TEMPLATE
    + "\n### Actividad\n**{activity_title}**\n{activity_description}"
)

TEMPLATE_FULL = (
    TEMPLATE_WITH_RUBRIC
    + "\n### Actividad\n**{activity_title}**\n{activity_description}"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def builder(mock_session: AsyncMock) -> ContextBuilder:
    return ContextBuilder(mock_session)


def _patch_exercise_query(mock_session: AsyncMock, exercise: MagicMock) -> None:
    """Make session.execute return *exercise* for the Exercise query."""
    exercise_result = MagicMock()
    exercise_result.scalar_one_or_none.return_value = exercise
    mock_session.execute = AsyncMock(return_value=exercise_result)


def _patch_exercise_and_snapshot_queries(
    mock_session: AsyncMock,
    exercise: MagicMock,
    snapshot: MagicMock | None,
) -> None:
    """Return exercise on first execute call, snapshot on second."""
    exercise_result = MagicMock()
    exercise_result.scalar_one_or_none.return_value = exercise

    snapshot_result = MagicMock()
    snapshot_result.scalar_one_or_none.return_value = snapshot

    mock_session.execute = AsyncMock(
        side_effect=[exercise_result, snapshot_result]
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_build_prompt_with_rubric(builder: ContextBuilder, mock_session: AsyncMock) -> None:
    """When exercise has a rubric it should appear in the composed prompt."""
    exercise = _make_exercise(rubric="Rúbrica de prueba aquí")
    snapshot = _make_snapshot("x = 1")
    _patch_exercise_and_snapshot_queries(mock_session, exercise, snapshot)

    result = await builder.build_prompt(
        exercise_id=exercise.id,
        student_id=uuid.uuid4(),
        base_prompt_template=TEMPLATE_WITH_RUBRIC,
    )

    assert "Rúbrica de prueba aquí" in result


@pytest.mark.anyio
async def test_build_prompt_without_rubric(builder: ContextBuilder, mock_session: AsyncMock) -> None:
    """When exercise has no rubric the rubric placeholder and section are removed."""
    exercise = _make_exercise(rubric=None)
    snapshot = _make_snapshot("y = 2")
    _patch_exercise_and_snapshot_queries(mock_session, exercise, snapshot)

    result = await builder.build_prompt(
        exercise_id=exercise.id,
        student_id=uuid.uuid4(),
        base_prompt_template=TEMPLATE_WITH_RUBRIC,
    )

    assert "{exercise_rubric}" not in result
    assert "None" not in result


@pytest.mark.anyio
async def test_build_prompt_no_snapshot_uses_starter_code(
    builder: ContextBuilder,
    mock_session: AsyncMock,
) -> None:
    """When there is no snapshot the starter_code should be used."""
    exercise = _make_exercise(starter_code="def suma(lst):\n    pass")
    _patch_exercise_and_snapshot_queries(mock_session, exercise, None)

    result = await builder.build_prompt(
        exercise_id=exercise.id,
        student_id=uuid.uuid4(),
        base_prompt_template=MINIMAL_TEMPLATE,
    )

    assert "def suma(lst):" in result


@pytest.mark.anyio
async def test_build_prompt_no_snapshot_no_starter(
    builder: ContextBuilder,
    mock_session: AsyncMock,
) -> None:
    """When neither snapshot nor starter_code exist, use the fallback message."""
    exercise = _make_exercise(starter_code="")
    _patch_exercise_and_snapshot_queries(mock_session, exercise, None)

    result = await builder.build_prompt(
        exercise_id=exercise.id,
        student_id=uuid.uuid4(),
        base_prompt_template=MINIMAL_TEMPLATE,
    )

    assert "El alumno aun no ha escrito codigo" in result


@pytest.mark.anyio
async def test_build_prompt_with_activity(
    builder: ContextBuilder,
    mock_session: AsyncMock,
) -> None:
    """When exercise has an associated activity its context appears in the prompt."""
    activity = _make_activity(title="TP 1 — Listas", description="Trabajamos listas en Python")
    exercise = _make_exercise(activity=activity, activity_id=uuid.uuid4())
    snapshot = _make_snapshot("n = 0")
    _patch_exercise_and_snapshot_queries(mock_session, exercise, snapshot)

    result = await builder.build_prompt(
        exercise_id=exercise.id,
        student_id=uuid.uuid4(),
        base_prompt_template=TEMPLATE_WITH_ACTIVITY,
    )

    assert "TP 1 — Listas" in result
    assert "Trabajamos listas en Python" in result


@pytest.mark.anyio
async def test_build_prompt_no_activity_section_removed(
    builder: ContextBuilder,
    mock_session: AsyncMock,
) -> None:
    """When exercise has no activity, activity placeholders are stripped."""
    exercise = _make_exercise(activity=None, activity_id=None)
    snapshot = _make_snapshot("pass")
    _patch_exercise_and_snapshot_queries(mock_session, exercise, snapshot)

    result = await builder.build_prompt(
        exercise_id=exercise.id,
        student_id=uuid.uuid4(),
        base_prompt_template=TEMPLATE_WITH_ACTIVITY,
    )

    assert "{activity_title}" not in result
    assert "{activity_description}" not in result


@pytest.mark.anyio
async def test_build_prompt_truncation(
    builder: ContextBuilder,
    mock_session: AsyncMock,
) -> None:
    """Code longer than 2000 chars is truncated and prefixed with the marker."""
    long_code = "x = 1\n" * 500  # well over 2000 chars
    assert len(long_code) > _CODE_TRUNCATE_LIMIT

    exercise = _make_exercise()
    snapshot = _make_snapshot(long_code)
    _patch_exercise_and_snapshot_queries(mock_session, exercise, snapshot)

    result = await builder.build_prompt(
        exercise_id=exercise.id,
        student_id=uuid.uuid4(),
        base_prompt_template=MINIMAL_TEMPLATE,
    )

    assert _TRUNCATION_PREFIX.strip() in result
    # Ensure the full un-truncated code is not in the result
    assert len(long_code) > _CODE_TRUNCATE_LIMIT
    # Exact last 2000 chars should be present
    assert long_code[-_CODE_TRUNCATE_LIMIT:] in result


@pytest.mark.anyio
async def test_build_prompt_short_code_not_truncated(
    builder: ContextBuilder,
    mock_session: AsyncMock,
) -> None:
    """Code within the 2000-char limit is not prefixed with the truncation marker."""
    code = "x = 1"
    exercise = _make_exercise()
    snapshot = _make_snapshot(code)
    _patch_exercise_and_snapshot_queries(mock_session, exercise, snapshot)

    result = await builder.build_prompt(
        exercise_id=exercise.id,
        student_id=uuid.uuid4(),
        base_prompt_template=MINIMAL_TEMPLATE,
    )

    assert _TRUNCATION_PREFIX.strip() not in result
    assert code in result


@pytest.mark.anyio
async def test_build_prompt_exercise_not_found(
    builder: ContextBuilder,
    mock_session: AsyncMock,
) -> None:
    """NotFoundError is raised when exercise does not exist."""
    not_found_result = MagicMock()
    not_found_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=not_found_result)

    with pytest.raises(NotFoundError):
        await builder.build_prompt(
            exercise_id=uuid.uuid4(),
            student_id=uuid.uuid4(),
            base_prompt_template=MINIMAL_TEMPLATE,
        )


@pytest.mark.anyio
async def test_build_prompt_topic_tags_joined(
    builder: ContextBuilder,
    mock_session: AsyncMock,
) -> None:
    """Multiple topic tags are joined with commas in the prompt."""
    exercise = _make_exercise(topic_tags=["listas", "recursion", "funciones"])
    snapshot = _make_snapshot("pass")
    _patch_exercise_and_snapshot_queries(mock_session, exercise, snapshot)

    result = await builder.build_prompt(
        exercise_id=exercise.id,
        student_id=uuid.uuid4(),
        base_prompt_template=MINIMAL_TEMPLATE,
    )

    assert "listas" in result
    assert "recursion" in result
    assert "funciones" in result


@pytest.mark.anyio
async def test_build_prompt_empty_topic_tags(
    builder: ContextBuilder,
    mock_session: AsyncMock,
) -> None:
    """When topic_tags is empty, the fallback label is used."""
    exercise = _make_exercise(topic_tags=[])
    snapshot = _make_snapshot("pass")
    _patch_exercise_and_snapshot_queries(mock_session, exercise, snapshot)

    result = await builder.build_prompt(
        exercise_id=exercise.id,
        student_id=uuid.uuid4(),
        base_prompt_template=MINIMAL_TEMPLATE,
    )

    assert "sin clasificar" in result


# ---------------------------------------------------------------------------
# Unit test for _truncate_code helper (no async needed)
# ---------------------------------------------------------------------------


def test_truncate_code_short_passthrough() -> None:
    code = "a = 1"
    assert _truncate_code(code) == code


def test_truncate_code_long_prefixed() -> None:
    code = "x\n" * 2000
    result = _truncate_code(code)
    assert result.startswith(_TRUNCATION_PREFIX)
    assert len(result) == len(_TRUNCATION_PREFIX) + _CODE_TRUNCATE_LIMIT


def test_truncate_code_exact_limit_no_prefix() -> None:
    code = "a" * _CODE_TRUNCATE_LIMIT
    assert _truncate_code(code) == code


def test_truncate_code_one_over_limit_prefixed() -> None:
    code = "a" * (_CODE_TRUNCATE_LIMIT + 1)
    result = _truncate_code(code)
    assert result.startswith(_TRUNCATION_PREFIX)
