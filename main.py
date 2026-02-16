from fastapi import FastAPI, Request
import os
import requests

app = FastAPI()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    # 일반 메시지
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text")

        if text:
            send_summary_button(chat_id, text)

    # 버튼 클릭
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        original_text = callback["data"]

        summary = summarize_text(original_text)
        edit_message(chat_id, message_id, summary)

    return {"ok": True}


def send_summary_button(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🧠 요약하기",
                    "callback_data": text[:100]
                }
            ]
        ]
    }

    requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard
    })


def summarize_text(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{
            "parts": [{
                "text": f"반드시 3줄 이하로 요약:\n{text}"
            }]
        }]
    }

    response = requests.post(url, json=payload)
    result = response.json()

    return result["candidates"][0]["content"]["parts"][0]["text"]


def edit_message(chat_id, message_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"

    requests.post(url, json={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    })
