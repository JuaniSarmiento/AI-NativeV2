"""Test case runner — executes each test case independently against student code."""
from __future__ import annotations

from dataclasses import dataclass

from app.features.sandbox.engine import ExecutionResult, SandboxService


@dataclass
class TestCaseResult:
    id: str
    description: str
    passed: bool
    actual_output: str
    expected_output: str | None  # None for hidden cases that failed
    status: str  # "pass" | "fail" | "error" | "timeout"


@dataclass
class RunResult:
    stdout: str  # stdout from last execution or first failure
    stderr: str
    exit_code: int
    runtime_ms: int
    status: str  # "passed" | "partial" | "failed" | "error" | "timeout" | "security_violation"
    test_results: list[TestCaseResult]
    total_passed: int
    total_cases: int


class TestRunner:
    def __init__(self) -> None:
        self._sandbox = SandboxService()

    def run_all(self, code: str, test_cases: dict) -> RunResult:
        """Execute code against all test cases and return aggregated results."""
        cases = test_cases.get("cases", [])
        if not cases:
            # No test cases — just run the code once
            result = self._sandbox.execute(code)
            return RunResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_code,
                runtime_ms=result.runtime_ms,
                status=result.status,
                test_results=[],
                total_passed=0,
                total_cases=0,
            )

        results: list[TestCaseResult] = []
        total_ms = 0
        last_stdout = ""
        last_stderr = ""
        last_exit = 0
        overall_failed = False
        overall_error = False

        for case in cases:
            case_id = case.get("id", "?")
            description = case.get("description", "")
            stdin_data = case.get("input", "")
            expected = case.get("expected_output", "")
            is_hidden = case.get("is_hidden", False)

            exec_result = self._sandbox.execute(code, stdin_data=stdin_data)
            total_ms += exec_result.runtime_ms
            last_stdout = exec_result.stdout
            last_stderr = exec_result.stderr
            last_exit = exec_result.exit_code

            if exec_result.status != "ok":
                # Execution error — this case fails
                results.append(TestCaseResult(
                    id=case_id,
                    description=description,
                    passed=False,
                    actual_output=exec_result.stderr[:200] if exec_result.stderr else exec_result.stdout[:200],
                    expected_output=None if is_hidden else expected,
                    status=exec_result.status,
                ))
                overall_error = True
                # For timeout/security, stop running more cases
                if exec_result.status in ("timeout", "security_violation", "memory_exceeded"):
                    break
                continue

            # Compare output (strip trailing whitespace from both)
            actual = exec_result.stdout.rstrip()
            expect = expected.rstrip()
            passed = actual == expect

            results.append(TestCaseResult(
                id=case_id,
                description=description,
                passed=passed,
                actual_output=actual,
                expected_output=None if (is_hidden and not passed) else expected,
                status="pass" if passed else "fail",
            ))

            if not passed:
                overall_failed = True

        total_passed = sum(1 for r in results if r.passed)
        total_cases = len(results)

        if overall_error:
            # Check if last error was specific
            last_status = results[-1].status if results else "error"
            if last_status in ("timeout", "security_violation", "memory_exceeded"):
                overall_status = last_status
            else:
                overall_status = "error"
        elif total_passed == total_cases:
            overall_status = "passed"
        elif total_passed > 0:
            overall_status = "partial"
        else:
            overall_status = "failed"

        return RunResult(
            stdout=last_stdout,
            stderr=last_stderr,
            exit_code=last_exit,
            runtime_ms=total_ms,
            status=overall_status,
            test_results=results,
            total_passed=total_passed,
            total_cases=total_cases,
        )
