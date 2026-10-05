import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.config import settings

def check_gemini_quota():
    print("Checking Gemini API and Quota status...")
    api_key = settings.GEMINI_API_KEY
    model_name = settings.GEMINI_MODEL
    print(f"Configured Model: {model_name}")
    print(f"API Key present: {bool(api_key)}")
    if api_key:
        print(f"API Key prefix: {api_key[:8]}... (length={len(api_key)})")

    try:
        import google.genai as genai
        version = getattr(genai, "__version__", "unknown")
        print(f"google-genai package version: {version}")
    except Exception as e:
        print(f"Failed to import google.genai: {e}")
        return

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        # Test client and check models
        print("Testing model accessibility via client.models.get / list...")
        try:
            # Check if model exists
            model_info = client.models.get(model=model_name)
            print(f"Model {model_name} retrieved successfully: {getattr(model_info, 'display_name', model_name)}")
        except Exception as me:
            print(f"models.get('{model_name}') notice: {me}")

        # Perform a single minimal quota verification call
        from google.genai import types
        print("Performing single minimal token generation probe to verify quota status...")
        resp = client.models.generate_content(
            model=model_name,
            contents="Say 'OK'",
            config=types.GenerateContentConfig(max_output_tokens=5, temperature=0.0)
        )
        print("Probe call SUCCESS! Response text:", getattr(resp, "text", "").strip())
        print("QUOTA EXHAUSTED = NO")
    except Exception as e:
        err_str = str(e)
        print(f"Probe call returned error: {err_str}")
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            print("QUOTA EXHAUSTED = YES")
            print(f"Exact error: {err_str}")
        else:
            print(f"QUOTA EXHAUSTED = UNKNOWN (Non-quota error: {type(e).__name__})")

if __name__ == "__main__":
    check_gemini_quota()
