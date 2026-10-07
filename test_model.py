from google import genai
import os
from dotenv import load_dotenv
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
prompt = 'Return JSON: {"test": "value"}'
resp = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=prompt,
    config={
        "response_mime_type": "application/json",
        "temperature": 0.1,
    }
)
print("Response:", resp.text[:200])