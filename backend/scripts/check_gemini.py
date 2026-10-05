import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path("backend").resolve()))

from app.config import settings
from google import genai
from google.genai import types

print(f"Loaded GEMINI_API_KEY: {settings.GEMINI_API_KEY[:8]}... (length: {len(settings.GEMINI_API_KEY)})")
print(f"Loaded GEMINI_MODEL: {settings.GEMINI_MODEL}")

# Check Part.from_bytes structure
part = types.Part.from_bytes(data=b"test-bytes", mime_type="image/jpeg")
print("Part attributes/dir:", [a for a in dir(part) if not a.startswith("_")])
print("Part inline_data:", getattr(part, "inline_data", None))
if hasattr(part, "inline_data") and part.inline_data:
    print("inline_data data:", getattr(part.inline_data, "data", None))

# Try listing models
client = genai.Client(api_key=settings.GEMINI_API_KEY)
try:
    print("\nAttempting to list models...")
    models = list(client.models.list())
    print(f"Found {len(models)} models.")
    for m in models[:15]:
        print("Model:", getattr(m, "name", m))
except Exception as e:
    print("List models error:", type(e).__name__, str(e))
