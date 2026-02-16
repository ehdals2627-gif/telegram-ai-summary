from fastapi import FastAPI, Request
import os
import requests

app = FastAPI()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text")

        if text:
            summary = summarize_text(text)
            send_message(chat_id, summary)

    return {"ok": True}


def summarize_text(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{
            "parts": [{"text": f"Summarize in 3 concise lines:\n{text}"}]
        }]
    }

    response = requests.post(url, json=payload)
    result = response.json()

    return result["candidates"][0]["content"]["parts"][0]["text"]


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })
