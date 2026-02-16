from fastapi import FastAPI
import os
import requests

app = FastAPI()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

@app.get("/")
def root():
    return {"status": "running"}

@app.post("/summarize")
async def summarize(data: dict):
    text = data.get("text")

    if not text:
        return {"error": "No text provided"}

    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not set"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"Summarize the following in 3 concise lines:\n\n{text}"}
                ]
            }
        ]
    }

    response = requests.post(url, json=payload)

    if response.status_code != 200:
        return {
            "error": "Gemini API error",
            "details": response.text
        }

    result = response.json()

    return {
        "summary": result["candidates"][0]["content"]["parts"][0]["text"]
    }
