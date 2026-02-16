from fastapi import FastAPI
import os
import requests

app = FastAPI()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

@app.post("/summarize")
async def summarize(data: dict):
    text = data["text"]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"Summarize in 3 concise lines:\n{text}"}
                ]
            }
        ]
    }

    response = requests.post(url, json=payload)
    result = response.json()

    summary = result["candidates"][0]["content"]["parts"][0]["text"]

    return {"summary": summary}
