from __future__ import annotations

from pydantic import BaseModel, Field


class RunCodeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50000)
    stdin: str | None = Field(None, max_length=10000, description="Optional stdin input for the program")


class RunCodeResponse(BaseModel):
    """Terminal-style output — no test case results.

    Test evaluation happens at submission time via AI grading.
    """
    stdout: str
    stderr: str
    exit_code: int
    runtime_ms: int
    status: str  # ok | timeout | memory_exceeded | syntax_error | runtime_error | security_violation
