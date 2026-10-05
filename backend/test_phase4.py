"""
Convenience trampoline for running test_phase4.py from the backend directory.
"""
import sys
from pathlib import Path

root_test = Path(__file__).resolve().parent.parent / "test_phase4.py"
if root_test.exists():
    with open(root_test, "r", encoding="utf-8") as f:
        code = f.read()
    sys.argv[0] = str(root_test)
    exec(compile(code, str(root_test), "exec"))
else:
    print(f"Error: Could not locate root test file at {root_test}")
    sys.exit(1)
