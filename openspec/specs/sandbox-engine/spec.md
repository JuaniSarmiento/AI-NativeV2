## ADDED Requirements

### Requirement: Secure Python execution sandbox
The system SHALL provide a `SandboxService` that executes arbitrary Python code in an isolated subprocess with: timeout of 10 seconds, memory limit of 128MB (via RLIMIT_AS), restricted file descriptors (max 32), working directory set to /tmp, and a blacklist of dangerous imports (os, subprocess, socket, shutil, pathlib, importlib, ctypes, sys.modules manipulation).

#### Scenario: Clean code executes successfully
- **WHEN** valid Python code is submitted
- **THEN** the sandbox SHALL return stdout, stderr, exit_code, and execution_time_ms

#### Scenario: Timeout kills the process
- **WHEN** code runs longer than 10 seconds (e.g. infinite loop)
- **THEN** the sandbox SHALL return status "timeout" and terminate the process

#### Scenario: Memory exceeded
- **WHEN** code allocates more than 128MB
- **THEN** the sandbox SHALL return status "memory_exceeded"

#### Scenario: Syntax error reported
- **WHEN** code has a Python syntax error
- **THEN** the sandbox SHALL return status "syntax_error" with the error in stderr

#### Scenario: Dangerous import blocked
- **WHEN** code tries to import os, subprocess, socket, or other blacklisted modules
- **THEN** the sandbox SHALL return status "security_violation" with an error message

### Requirement: Test runner
The system SHALL provide a test runner that executes each test case independently: sends the case's `input` via stdin, captures stdout, and compares with `expected_output` (exact string match, stripped of trailing whitespace).

#### Scenario: All test cases pass
- **WHEN** code produces correct output for all test cases
- **THEN** each case SHALL have result "pass" and overall status SHALL be "passed"

#### Scenario: Partial pass
- **WHEN** code passes some test cases but fails others
- **THEN** each case SHALL have its individual result and overall status SHALL be "partial"

#### Scenario: Hidden test cases not revealed
- **WHEN** a hidden test case fails
- **THEN** the result SHALL show "fail" but NOT reveal the expected_output
