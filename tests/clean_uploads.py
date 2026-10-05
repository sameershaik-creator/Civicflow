"""
Cleans any residual test files from the runtime uploads directory.
Ensures zero test images or residual test data contaminate runtime storage.
"""
import os
import shutil
from pathlib import Path

backend_uploads = Path(__file__).resolve().parent.parent / "backend" / "uploads" / "complaints"
root_uploads = Path(__file__).resolve().parent.parent / "uploads" / "complaints"

for d in [backend_uploads, root_uploads]:
    if d.exists() and d.is_dir():
        for item in d.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                    print(f"Removed residual test file: {item.name}")
                except Exception as e:
                    print(f"Error removing {item.name}: {e}")
print("Runtime uploads directories cleaned successfully.")
