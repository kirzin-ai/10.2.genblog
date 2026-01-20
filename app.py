import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import requests
from typing import Dict, Any
from datetime import datetime

# Инициализируем FastAPI приложение
app = FastAPI(
    title="Blog Post Generator",
    description="Сервис для автоматической генерации блог-постов на основе актуальных новостей с NewsData.io и OpenAI",
    version="2.0.0"
)

# Получаем API ключи из переменных окружения
openai.api_key = os.getenv("OPENAI_API_KEY")
newsdata_api_key = os.getenv("NEWSDATA_API_KEY")  # Изменено с CURRENTS_API_KEY

# Проверяем, что оба API ключа заданы
if not openai.api_key or not newsdata_api_key:
    raise ValueError("Переменные окружения OPENAI_API_KEY и NEWSDATA_API_KEY должны быть установлены")

# Pydantic модель для валидации входных данных
class Topic(BaseModel):
    topic: str  # Тема для генерации поста

# Функция для получения последних новостей через NewsData.io API
def get_recent_news(topic: str) -> str:
    """
    Запрашивает актуальные новости по ключевому слову через NewsData.io API.
    
    Args:
        topic (str): Ключевое слово для поиска новостей
        
    Returns:
        str: Заголовки первых 5 новостей, разделенные переносами строк
        
    Raises:
        HTTPException: При ошибке API запроса
    """
    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": newsdata_api_key,
        "q": topic,           # Поисковый запрос
        "language": "en",     # Язык новостей
        "size": 5,            # Количество новостей (макс 10 в бесплатном тарифе)
        "page": 1             # Первая страница
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            raise HTTPException(
                status_code=500, 
                detail=f"Ошибка NewsData.io API: {response.status_code} - {response.text}"
            )
        
        news_data = response.json()
        
        # Проверяем наличие ошибок в ответе
        if news_data.get("error"):
            raise HTTPException(status_code=500, detail=f"NewsData.io ошибка: {news_data['error']}")
        
        articles = news_data.get("results", [])
        if not articles:
            return f"Свежих новостей по теме '{topic}' не найдено."
        
        # Формируем список заголовков с источниками
        news_titles = []
        for article in articles:
            title = article.get("title", "Без заголовка")
            source = article.get("source_id", "Неизвестный источник")
            news_titles.append(f"• {title} ({source})")
        
        return "\n".join(news_titles)
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сети при запросе новостей: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Неожиданная ошибка API новостей: {str(e)}")

# Функция для генерации контента статьи с использованием OpenAI
def generate_content(topic: str) -> Dict[str, Any]:
    """
    Генерирует полный блог-пост: заголовок, мета-описание и основной контент.
    """
    # Получаем актуальные новости
    recent_news = get_recent_news(topic)
    print(f"📡 Найдено новостей по теме '{topic}': {len(recent_news.splitlines())}")

    try:
        # 1. Генерация заголовка
        title_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user", 
                "content": f"""Создайте яркий заголовок для статьи на тему '{topic}'.

АКТУАЛЬНЫЕ НОВОСТИ:
{recent_news}

Требования:
• До 60 символов
• Содержит ключевые слова из темы
• Создает интригу
• SEO-оптимизирован"""
            }],
            max_tokens=60,
            temperature=0.7,
            stop=["\n", "\n\n"]
        )
        title = title_response.choices[0].message.content.strip()

        # 2. Генерация мета-описания
        meta_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user", 
                "content": f"""Напишите мета-описание (150-160 символов) для статьи:

ЗАГОЛОВОК: '{title}'
ТЕМА: '{topic}'

Должно содержать:
• Ключевые слова
• Ценность статьи
• Призыв к действию"""
            }],
            max_tokens=120,
            temperature=0.5
        )
        meta_description = meta_response.choices[0].message.content.strip()

        # 3. Генерация полного контента
        content_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user", 
                "content": f"""Напишите полноценную статью на тему '{topic}' (1500+ символов).

=== АКТУАЛЬНЫЙ КОНТЕКСТ НОВОСТЕЙ ===
{recent_news}

=== СТРУКТУРА СТАТЬИ (ОБЯЗАТЕЛЬНО): ===
1️⃣ **Введение** (200-300 слов) - хук + актуальность
2️⃣ **Основная часть** (3-4 подзаголовка):
   • Анализ текущей ситуации
   • Ключевые тренды из новостей  
   • Практические кейсы
   • Экспертные выводы
3️⃣ **Заключение** - итоги + CTA

=== ТРЕБОВАНИЯ ===
• Каждый абзац: 3-5 предложений
• Markdown форматирование (##, ###, **жирный**)
• Естественная плотность ключевых слов
• Ссылки на новости в тексте
• Легкий стиль для широкой аудитории"""
            }],
            max_tokens=2500,
            temperature=0.6,
            presence_penalty=0.4,
            frequency_penalty=0.4
        )
        post_content = content_response.choices[0].message.content.strip()

        return {
            "title": title,
            "meta_description": meta_description,
            "post_content": post_content,
            "news_context": recent_news[:800] + "..." if len(recent_news) > 800 else recent_news,
            "word_count": len(post_content.split()),
            "generated_at": datetime.now().isoformat(),
            "api_used": "NewsData.io + OpenAI GPT-4o-mini"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка OpenAI API: {str(e)}")

# Основной эндпоинт для генерации поста
@app.post("/generate-post", response_model=Dict[str, Any])
async def generate_post_api(topic: Topic):
    """Генерирует блог-пост по заданной теме."""
    try:
        result = generate_content(topic.topic)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Неожиданная ошибка: {str(e)}")

# Корневой эндпоинт
