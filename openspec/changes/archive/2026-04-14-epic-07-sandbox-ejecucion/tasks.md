## 1. Sandbox Engine

- [x] 1.1 Create `backend/app/features/sandbox/engine.py` with SandboxService: subprocess execution with timeout 10s, memory 128MB (RLIMIT_AS), restricted file descriptors, chdir /tmp
- [x] 1.2 Create `backend/app/features/sandbox/blacklist.py` with import blacklist wrapper script that overrides __import__ to block dangerous modules

## 2. Test Runner

- [x] 2.1 Create `backend/app/features/sandbox/runner.py` with TestRunner: executes each test case independently (stdin → stdout comparison), returns individual pass/fail results, hides expected_output for hidden cases

## 3. Schemas

- [x] 3.1 Create `backend/app/features/sandbox/schemas.py` with RunCodeRequest, RunCodeResponse, TestCaseResult

## 4. Router + Events

- [x] 4.1 Create `backend/app/features/sandbox/router.py` with POST /api/v1/student/exercises/{id}/run, enrollment check, event emission (code.executed / code.execution.failed)
- [x] 4.2 Register sandbox router in `backend/app/main.py`

## 5. Frontend — Editor + Output

- [x] 5.1 Update `frontend/src/features/activities/StudentActivityViewPage.tsx` replacing placeholder with code editor (textarea monospace, pre-filled with starter_code) + "Ejecutar" button + output panel
- [x] 5.2 Create `frontend/src/features/sandbox/types.ts` with RunResult, TestCaseResult types
- [x] 5.3 Create `frontend/src/features/sandbox/useRunCode.ts` hook that calls the run endpoint and manages loading/result state

## 6. Tests

- [x] 6.1 Create `backend/tests/unit/test_sandbox_engine.py` with tests for: clean execution, timeout, syntax error, dangerous import blocked
- [x] 6.2 Create `backend/tests/integration/test_sandbox_api.py` with tests for: successful run with test results, event emission, non-enrolled rejection
