import os
import asyncio
from google import genai
from dotenv import load_dotenv

async def test_new_sdk():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
    
    if not api_key:
        print("API Key missing")
        return

    client = genai.Client(api_key=api_key)
    
    print(f"Testing new Google GenAI SDK with model: {model_name}...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'New SDK is working!'"
        )
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_new_sdk())
