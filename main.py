from fastapi import FastAPI, Request
import os
import requests
import time

app = FastAPI()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# =============================
# In-memory storage (무료 플랜용)
# =============================

user_sessions = {}
user_limits = {}

DAILY_LIMIT = 20
RESET_SECONDS = 86400


# =============================
# 유틸
# =============================

def check_rate_limit(user_id):
    now = time.time()

    if user_id not in user_limits:
        user_limits[user_id] = {"count": 0, "reset": now + RESET_SECONDS}

    data = user_limits[user_id]

    if now > data["reset"]:
        data["count"] = 0
        data["reset"] = now + RESET_SECONDS

    if data["count"] >= DAILY_LIMIT:
        return False

    data["count"] += 1
    return True


def split_text(text, chunk_size=3000):
    sentences = text.split(". ")
    chunks = []
    current = ""

    for s in sentences:
        if len(current) + len(s) < chunk_size:
            current += s + ". "
        else:
            chunks.append(current)
            current = s + ". "

    if current:
        chunks.append(current)

    return chunks


def build_prompt(text, mode="standard"):
    if mode == "short":
        bullet = 3
    elif mode == "detailed":
        bullet = 8
    else:
        bullet = 5

    return f"""
You are a professional summarization engine.

Summarize the content below.

Output format:
- {bullet} concise bullet points
- 1 core takeaway sentence
- No opinions
- No fluff
- Preserve key facts

Content:
{text}
"""


def call_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = requests.post(url, json=payload, timeout=20)
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return "요약 중 오류가 발생했습니다."


def summarize_text(text, mode="standard"):
    if len(text) < 3000:
        prompt = build_prompt(text, mode)
        return call_gemini(prompt)

    # 2-pass summarization
    chunks = split_text(text)
    partial_summaries = []

    for chunk in chunks:
        partial_summaries.append(call_gemini(build_prompt(chunk, "short")))

    final_prompt = build_prompt("\n".join(partial_summaries), mode)
    return call_gemini(final_prompt)


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })


# =============================
# Webhook
# =============================

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    if not check_rate_limit(user_id):
        send_message(chat_id, "⚠ 하루 요약 한도 초과입니다.")
        return {"ok": True}

    # ===== 명령어 처리 =====

    if text.startswith("/collect"):
        user_sessions[user_id] = {
            "collecting": True,
            "messages": [],
            "mode": "standard"
        }
        send_message(chat_id, "📥 수집 모드 시작. 메시지를 보내세요.\n완료 시 /summarize")
        return {"ok": True}

    if text.startswith("/short"):
        user_sessions.setdefault(user_id, {})["mode"] = "short"
        send_message(chat_id, "📉 짧은 요약 모드 설정 완료")
        return {"ok": True}

    if text.startswith("/detailed"):
        user_sessions.setdefault(user_id, {})["mode"] = "detailed"
        send_message(chat_id, "📈 상세 요약 모드 설정 완료")
        return {"ok": True}

    if text.startswith("/standard"):
        user_sessions.setdefault(user_id, {})["mode"] = "standard"
        send_message(chat_id, "📊 표준 요약 모드 설정 완료")
        return {"ok": True}

    if text.startswith("/summarize"):
        session = user_sessions.get(user_id)

        if not session or not session.get("messages"):
            send_message(chat_id, "수집된 메시지가 없습니다.")
            return {"ok": True}

        combined = "\n".join(session["messages"])
        mode = session.get("mode", "standard")

        result = summarize_text(combined, mode)
        send_message(chat_id, result)

        user_sessions[user_id] = {}
        return {"ok": True}

    # ===== 수집 모드일 경우 =====

    if user_sessions.get(user_id, {}).get("collecting"):
        user_sessions[user_id]["messages"].append(text)
        return {"ok": True}

    # ===== 기본 단일 메시지 요약 =====

    mode = user_sessions.get(user_id, {}).get("mode", "standard")
    result = summarize_text(text, mode)
    send_message(chat_id, result)

    return {"ok": True}
