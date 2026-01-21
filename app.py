import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import requests
from typing import Dict, Any
from datetime import datetime

app = FastAPI(
    title="Blog Post Generator",
    description="Сервис для автоматической генерации блог-постов с NewsData.io + OpenAI",
    version="2.1.0"
)

# API ключи
openai.api_key = os.getenv("OPENAI_API_KEY")
newsdata_api_key = os.getenv("NEWSDATA_API_KEY")

if not openai.api_key or not newsdata_api_key:
    raise ValueError("OPENAI_API_KEY и NEWSDATA_API_KEY должны быть установлены")

class Topic(BaseModel):
    topic: str

@app.get("/")
async def root():
    return {"status": "OK", "docs": "/docs", "post": "/generate-post (POST)"}

@app.get("/heartbeat")
async def heartbeat():
    return {"status": "healthy", "news_api": "NewsData.io"}

def get_recent_news(topic: str) -> str:
    """Получает новости БЕЗ page параметра (фикс 422 ошибки)."""
    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": newsdata_api_key,
        "q": topic,
        "language": "en",
        "size": 5
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"NewsData.io API: {response.status_code}")
        
        data = response.json()
        if data.get("status") != "success":
            raise HTTPException(status_code=500, detail=f"NewsData.io: {data.get('results', {}).get('message', 'Error')}")
        
        articles = data.get("results", [])
        if not articles:
            return f"Новостей по теме '{topic}' не найдено."
        
        news_list = [f"• {a.get('title', 'No title')} ({a.get('source_id', 'Unknown')})" for a in articles]
        return "\n".join(news_list)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка новостей: {str(e)}")

def generate_content(topic: str) -> Dict[str, Any]:
    recent_news = get_recent_news(topic)
    
    title = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Заголовок статьи '{topic}' на основе новостей:\n{recent_news[:300]}"}],
        max_tokens=60,
        temperature=0.7
    ).choices[0].message.content.strip()
    
    content = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Статья '{topic}' (1500+ символов) на основе:\n{recent_news}"}],
        max_tokens=2000,
        temperature=0.6
    ).choices[0].message.content.strip()
    
    return {
        "title": title,
        "content": content,
        "news": recent_news[:500] + "..." if len(recent_news) > 500 else recent_news,
        "words": len(content.split())
    }

@app.post("/generate-post")
async def generate_post(topic: Topic):
    return generate_content(topic.topic)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
