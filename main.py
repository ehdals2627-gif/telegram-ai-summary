from fastapi import FastAPI
import google.generativeai as genai
import os

app = FastAPI()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-pro")

@app.post("/summarize")
async def summarize(data: dict):
    text = data["text"]

    response = model.generate_content(
        f"Summarize in 3 concise lines:\n\n{text}"
    )

    return {"summary": response.text}
