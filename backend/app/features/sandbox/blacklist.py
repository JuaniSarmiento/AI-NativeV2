"""Sandbox wrapper script — executed by the subprocess.

Sets resource limits and blocks dangerous imports before running student code.
Usage: python3 blacklist.py <code_file.py>
"""
import builtins
import os
import resource
import sys

# ---------------------------------------------------------------------------
# 1. Set resource limits
# ---------------------------------------------------------------------------
memory_mb = int(os.environ.get("SANDBOX_MEMORY_MB", "128"))
memory_bytes = memory_mb * 1024 * 1024

try:
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
except (ValueError, resource.error):
    pass  # Some systems don't support RLIMIT_AS

# Limit open file descriptors (blocks socket creation)
try:
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
except (ValueError, resource.error):
    pass

# ---------------------------------------------------------------------------
# 2. Block dangerous imports
# ---------------------------------------------------------------------------
BLOCKED_MODULES = frozenset({
    "os", "subprocess", "socket", "shutil", "pathlib",
    "importlib", "ctypes", "multiprocessing", "threading",
    "signal", "fcntl", "termios", "pty", "pipes",
    "http", "urllib", "requests", "httpx",
    "pickle", "shelve", "marshal",
    "code", "codeop", "compile", "compileall",
    "webbrowser", "antigravity",
    "tkinter", "turtle",
    "_thread", "_io",
})

_original_import = builtins.__import__


def _guarded_import(name, *args, **kwargs):
    top_level = name.split(".")[0]
    if top_level in BLOCKED_MODULES:
        raise ImportError(
            f"SecurityError: blocked import of '{name}'. "
            f"This module is not allowed in the sandbox."
        )
    return _original_import(name, *args, **kwargs)


builtins.__import__ = _guarded_import

# Also block open() for writing outside /tmp
_original_open = builtins.open


def _guarded_open(file, mode="r", *args, **kwargs):
    if any(m in str(mode) for m in ("w", "a", "x")) and not str(file).startswith("/tmp"):
        raise PermissionError("SecurityError: writing outside /tmp is not allowed.")
    return _original_open(file, mode, *args, **kwargs)


builtins.open = _guarded_open

# ---------------------------------------------------------------------------
# 3. Execute student code
# ---------------------------------------------------------------------------
if len(sys.argv) < 2:
    print("Usage: python3 blacklist.py <code_file.py>", file=sys.stderr)
    sys.exit(1)

code_file = sys.argv[1]

try:
    with _original_open(code_file, "r") as f:
        code = f.read()
    exec(compile(code, code_file, "exec"), {"__builtins__": builtins, "__name__": "__main__"})
except SystemExit:
    pass  # Allow sys.exit() in student code
except Exception as exc:
    print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
    sys.exit(1)
