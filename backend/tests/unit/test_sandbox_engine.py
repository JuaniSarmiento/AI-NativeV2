from __future__ import annotations

from unittest.mock import patch

import pytest

from app.features.sandbox.engine import SandboxService


@pytest.fixture
def sandbox():
    with patch("app.features.sandbox.engine.get_settings") as mock:
        mock.return_value.sandbox_timeout_seconds = 5
        mock.return_value.sandbox_memory_limit_mb = 128
        yield SandboxService()


def test_clean_execution(sandbox):
    result = sandbox.execute('print("hello world")')
    assert result.status == "ok"
    assert "hello world" in result.stdout
    assert result.exit_code == 0


def test_stdin_input(sandbox):
    code = 'name = input()\nprint(f"hi {name}")'
    result = sandbox.execute(code, stdin_data="alice")
    assert result.status == "ok"
    assert "hi alice" in result.stdout


def test_syntax_error(sandbox):
    result = sandbox.execute("def broken(\n  pass")
    assert result.status == "syntax_error"
    assert result.exit_code != 0


def test_runtime_error(sandbox):
    result = sandbox.execute("x = 1 / 0")
    assert result.status == "runtime_error"
    assert "ZeroDivisionError" in result.stderr


def test_dangerous_import_blocked(sandbox):
    result = sandbox.execute("import os\nprint(os.listdir('/'))")
    assert result.status in ("security_violation", "runtime_error")
    assert "SecurityError" in result.stderr or "blocked" in result.stderr.lower()


def test_subprocess_import_blocked(sandbox):
    result = sandbox.execute("import subprocess\nsubprocess.run(['ls'])")
    assert result.status in ("security_violation", "runtime_error")


def test_socket_import_blocked(sandbox):
    result = sandbox.execute("import socket\nsocket.socket()")
    assert result.status in ("security_violation", "runtime_error")


def test_timeout(sandbox):
    result = sandbox.execute("while True: pass")
    assert result.status == "timeout"
