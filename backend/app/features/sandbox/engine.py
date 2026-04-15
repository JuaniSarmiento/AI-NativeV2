"""Secure Python code execution sandbox.

Executes arbitrary Python code in an isolated subprocess with:
- Timeout: 10 seconds
- Memory: 128MB (RLIMIT_AS)
- No network access (restricted file descriptors)
- Working directory: /tmp
- Dangerous imports blocked via wrapper
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)

_BLACKLIST_WRAPPER = Path(__file__).parent / "blacklist.py"


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    runtime_ms: int
    status: str  # "ok" | "timeout" | "memory_exceeded" | "syntax_error" | "runtime_error" | "security_violation"


class SandboxService:
    def __init__(self) -> None:
        settings = get_settings()
        self._timeout = settings.sandbox_timeout_seconds
        self._memory_mb = settings.sandbox_memory_limit_mb

    def execute(self, code: str, stdin_data: str = "") -> ExecutionResult:
        """Execute Python code in a sandboxed subprocess."""
        # Write code to a temp file so the wrapper can import-guard it
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", dir="/tmp", delete=False
        ) as f:
            f.write(code)
            code_path = f.name

        try:
            start = time.monotonic()

            result = subprocess.run(
                [
                    "python3",
                    str(_BLACKLIST_WRAPPER),
                    code_path,
                ],
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd="/tmp",
                env={
                    "PATH": "/usr/local/bin:/usr/bin:/bin",
                    "HOME": "/tmp",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "SANDBOX_MEMORY_MB": str(self._memory_mb),
                },
            )

            elapsed_ms = int((time.monotonic() - start) * 1000)

            # Detect status from exit code and stderr
            status = "ok"
            if result.returncode != 0:
                stderr_lower = result.stderr.lower()
                if "securityerror" in stderr_lower or "blocked import" in stderr_lower:
                    status = "security_violation"
                elif "syntaxerror" in stderr_lower:
                    status = "syntax_error"
                elif "memoryerror" in stderr_lower or "cannot allocate" in stderr_lower:
                    status = "memory_exceeded"
                else:
                    status = "runtime_error"

            return ExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                runtime_ms=elapsed_ms,
                status=status,
            )

        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return ExecutionResult(
                stdout="",
                stderr="Execution timed out (limit: {}s)".format(self._timeout),
                exit_code=-1,
                runtime_ms=elapsed_ms,
                status="timeout",
            )
        except Exception as exc:
            logger.exception("Sandbox execution failed unexpectedly")
            return ExecutionResult(
                stdout="",
                stderr=str(exc)[:500],
                exit_code=-1,
                runtime_ms=0,
                status="runtime_error",
            )
        finally:
            # Clean up temp file
            try:
                Path(code_path).unlink(missing_ok=True)
            except Exception:
                pass
