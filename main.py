from fastapi import FastAPI, Request
import os
import requests
import time
from bs4 import BeautifulSoup

app = FastAPI()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

user_sessions = {}
daily_usage = {}
DAILY_LIMIT = 20


@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()

    # ===============================
    # 버튼 처리
    # ===============================
    if "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        user_id = callback["from"]["id"]
        action = callback["data"]

        if action == "summarize_now":
            session = user_sessions.get(user_id)
            if not session or not session.get("messages"):
                send_message(chat_id, "요약할 메시지가 없습니다.")
            else:
                combined = "\n".join(session["messages"])
                mode = session.get("mode", "standard")
                result = summarize_text(combined, mode)
                send_message(chat_id, result)
                user_sessions[user_id] = {}

        if action == "clear_session":
            user_sessions[user_id] = {}
            send_message(chat_id, "세션 초기화 완료.")

        return {"ok": True}

    # ===============================
    # 메시지 처리
    # ===============================
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        text = message.get("text")

        if not text:
            return {"ok": True}

        # 사용 제한
        today = time.strftime("%Y-%m-%d")
        if user_id not in daily_usage:
            daily_usage[user_id] = {"date": today, "count": 0}

        if daily_usage[user_id]["date"] != today:
            daily_usage[user_id] = {"date": today, "count": 0}

        if daily_usage[user_id]["count"] >= DAILY_LIMIT:
            send_message(chat_id, "오늘 사용량 초과 (20회)")
            return {"ok": True}

        # 모드 설정
        if text.startswith("/short"):
            user_sessions[user_id] = {"mode": "short"}
            send_message(chat_id, "3줄 요약 모드 설정")
            return {"ok": True}

        if text.startswith("/standard"):
            user_sessions[user_id] = {"mode": "standard"}
            send_message(chat_id, "5줄 요약 모드 설정")
            return {"ok": True}

        if text.startswith("/detailed"):
            user_sessions[user_id] = {"mode": "detailed"}
            send_message(chat_id, "8줄 요약 모드 설정")
            return {"ok": True}

        if text.startswith("/collect"):
            user_sessions[user_id] = {
                "collecting": True,
                "messages": [],
                "mode": "standard"
            }

            buttons = [
                [{"text": "📄 지금 요약", "callback_data": "summarize_now"}],
                [{"text": "🗑 초기화", "callback_data": "clear_session"}]
            ]

            send_message(chat_id, "수집 모드 시작. 메시지를 보내세요.", buttons)
            return {"ok": True}

        # 수집 모드
        session = user_sessions.get(user_id)
        if session and session.get("collecting"):
            session["messages"].append(text)
            send_message(chat_id, "메시지 저장됨.")
            return {"ok": True}

        # ===============================
        # 🔥 링크 자동 감지
        # ===============================
        if "http://" in text or "https://" in text:
            article_text = extract_text_from_url(text)

            if article_text:
                summary = summarize_text(article_text)
                daily_usage[user_id]["count"] += 1
                send_message(chat_id, summary)
            else:
                send_message(chat_id, "링크 본문 추출 실패.")

            return {"ok": True}

        # 기본 자동 요약
        mode = session.get("mode") if session else "standard"
        summary = summarize_text(text, mode)
        daily_usage[user_id]["count"] += 1
        send_message(chat_id, summary)

    return {"ok": True}


# ===============================
# 링크 본문 추출
# ===============================
def extract_text_from_url(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # script/style 제거
        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(line for line in lines if len(line) > 50)

        return text[:8000]  # 너무 길면 잘라냄

    except:
        return None


# ===============================
# Gemini 요약
# ===============================
def summarize_text(text, mode="standard"):

    if mode == "short":
        instruction = "Summarize in 3 concise lines."
    elif mode == "detailed":
        instruction = "Summarize in 8 detailed lines."
    else:
        instruction = "Summarize in 5 concise lines."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{
            "parts": [{"text": f"{instruction}\n{text}"}]
        }]
    }

    response = requests.post(url, json=payload)
    result = response.json()

    return result["candidates"][0]["content"]["parts"][0]["text"]


# ===============================
# Telegram 메시지 전송
# ===============================
def send_message(chat_id, text, buttons=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": buttons
        }

    requests.post(url, json=payload)
