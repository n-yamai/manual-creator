import os
from google import genai

api_key = os.getenv("GEMINI_API_KEY", "")
masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "NOT_SET"
print(f"Using API Key: {masked_key}")

client = genai.Client(api_key=api_key)

try:
    print("Listing models...")
    # List models via google-genai SDK
    for model in client.models.list():
        print(f"Model: {model.name}")
except Exception as e:
    print(f"Error: {e}")
