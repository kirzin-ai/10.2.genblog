from fastapi import FastAPI
from pydantic import BaseModel
import os
import requests

app = FastAPI()

class Topic(BaseModel):
    topic: str

@app.get("/")
async def root():
    return {
        "status": "LIVE ✅", 
        "openai_key": bool(os.getenv("OPENAI_API_KEY")), 
        "newsdata_key": bool(os.getenv("NEWSDATA_API_KEY"))
    }

@app.get("/heartbeat")
async def heartbeat():
    return {"status": "healthy"}

def get_news_safe(topic: str) -> str:
    """Безопасный запрос NewsData"""
    try:
        key = os.getenv("NEWSDATA_API_KEY")
        if not key:
            return "NewsData ключ отсутствует"
        
        url = "https://newsdata.io/api/1/news"
        params = {"apikey": key, "q": topic, "language": "en", "size": 3}
        resp = requests.get(url, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                articles = data.get("results", [])
                return "\n".join([f"• {a.get('title', 'No title')}" for a in articles[:3]])
        
        return "Новости временно недоступны"
    except:
        return "Генерируем без новостей"

@app.post("/generate-post")
async def generate_post(topic: Topic):
    try:
        # 1. Новости (опционально)
        news = get_news_safe(topic.topic)
        
        # 2. OpenAI НОВЫЙ API (1.0.0+)
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            return {"title": f"{topic.topic}", "content": f"OpenAI недоступен.\n\nНовости:\n{news}", "status": "OK-no-openai"}
        
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        
        # ✅ ПРАВИЛЬНЫЙ новый API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""Напишите статью о '{topic.topic}'.

Новости для контекста:
{news}

Формат:
## Заголовок
Введение...

### Подзаголовок 1
текст...

Макс 1200 символов."""
            }],
            max_tokens=1200,
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        
        return {
            "title": f"{topic.topic} | Актуальные новости 2026",
            "content": content,
            "news_used": news,
            "word_count": len(content.split()),
            "status": "FULL SUCCESS ✅"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "news": get_news_safe(topic.topic),
            "status": "ERROR",
            "hint": "Проверьте OpenAI ключ"
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
