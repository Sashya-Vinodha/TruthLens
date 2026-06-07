import os
import requests
from dotenv import load_dotenv

# Load the API key from your .env file
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("❌ ERROR: Could not find GEMINI_API_KEY in .env file.")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
headers = {'Content-Type': 'application/json'}
data = {
    "contents": [{"parts": [{"text": "What is 2+2? Reply with only the number."}]}]
}

print(f"Testing Gemini API with key ending in: ...{api_key[-5:]}")
response = requests.post(url, headers=headers, json=data)

print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    answer = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    print(f"✅ Success! Gemini says: {answer}")
else:
    print(f"🔥 Error: {response.text}")