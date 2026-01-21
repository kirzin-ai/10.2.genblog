from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

app = FastAPI()

class Topic(BaseModel):
    topic: str

@app.get("/")
async def root():
    return {"status": "LIVE ✅", "openai_key": bool(os.getenv("OPENAI_API_KEY")), "newsdata_key": bool(os.getenv("NEWSDATA_API_KEY"))}

@app.get("/heartbeat")
async def heartbeat():
    return {"status": "healthy"}

@app.post("/generate-post")
async def generate_post(topic: Topic):
    try:
        # Безопасная проверка ключей
        openai_key = os.getenv("OPENAI_API_KEY")
        newsdata_key = os.getenv("NEWSDATA_API_KEY")
        
        if not openai_key:
            return {"error": "Нет OpenAI ключа", "status": "missing_openai"}
        
        # Импорт openai ЛОКально (без краша при старте)
        import openai
        openai.api_key = openai_key
        
        # МИНИМАЛЬНАЯ генерация (без NewsData)
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"Заголовок статьи: {topic.topic}. Макс 50 слов."
            }],
            max_tokens=100,
            temperature=0.7
        )
        
        title = response.choices[0].message.content.strip()
        
        return {
            "title": title,
            "topic": topic.topic,
            "status": "SUCCESS ✅",
            "keys_ok": {"openai": True, "newsdata": bool(newsdata_key)}
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "topic": topic.topic,
            "status": "ERROR",
            "debug": "Проверьте OpenAI ключ в Render Environment"
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
