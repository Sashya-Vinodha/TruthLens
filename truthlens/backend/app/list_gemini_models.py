# list_gemini_models.py
import os
import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("GEMINI_API_KEY not set in environment. export GEMINI_API_KEY=... and retry.")

genai.configure(api_key=api_key)

print("Calling genai.list_models() ... (may take 1-2s)")
models = genai.list_models()
# print readable summary
for m in models:
    try:
        name = m.get("name") or m["model"]
    except Exception:
        name = str(m)
    print(name)
# pretty print raw
import json
print("\nFull JSON (first 2000 chars):")
print(json.dumps(models, indent=2)[:2000])
