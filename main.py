from fastapi import FastAPI
from openai import OpenAI
import os

app = FastAPI()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

@app.post("/summarize")
async def summarize(data: dict):
    text = data["text"]

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize in 3 concise lines."},
            {"role": "user", "content": text}
        ]
    )

    return {"summary": completion.choices[0].message.content}
