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
    """NewsData работает ✅"""
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
        # 1. Новости (работает ✅)
        news = get_news_safe(topic.topic)
        
        # 2. OpenAI ФИКС proxies
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            return {
                "title": f"{topic.topic} | Новости 2026", 
                "content": f"OpenAI недоступен.\n\n{news}",
                "news_used": news,
                "status": "OK-no-openai"
            }
        
        # ✅ ФИКС: передаем только api_key
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)  # Без proxies!
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""Статья о '{topic.topic}'.

Новости:
{news}

Формат: Markdown, 800-1200 символов, 3 подзаголовка."""
            }],
            max_tokens=1200,
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        
        return {
            "title": f"{topic.topic} | Актуально 2026",
            "content": content,
            "news_used": news,
            "word_count": len(content.split()),
            "status": "🚀 FULL SUCCESS!"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "news": get_news_safe(topic.topic),
            "status": "ERROR",
            "hint": "OpenAI проблема"
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
