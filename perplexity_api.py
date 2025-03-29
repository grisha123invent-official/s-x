import os
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# API-ключ
API_KEY = os.getenv("PERPLEXITY_API_KEY")

# URL для API-запросов
API_URL = "https://api.perplexity.ai/chat/completions"

def get_place_description(place_name, location):
    """
    Получает описание места с помощью Perplexity API
    
    Args:
        place_name (str): Название места
        location (str): Местоположение/адрес
        
    Returns:
        str: Описание места
    """
    prompt = f"Опиши достопримечательность '{place_name}' по адресу {location}. Напиши интересную информацию об истории и значимости этого места. Ответ на русском языке, до 200 слов."
    
    return _make_api_request(prompt)

def get_excursion_info(place_name, location):
    """
    Генерирует мини-экскурсию по месту с помощью Perplexity API
    
    Args:
        place_name (str): Название места
        location (str): Местоположение/адрес
        
    Returns:
        str: Текст экскурсии
    """
    prompt = f"Проведи мини-экскурсию по достопримечательности '{place_name}' по адресу {location}. Расскажи о истории создания, архитектурных особенностях, интересных фактах и культурной значимости. Ответ должен быть информативным и увлекательным, в стиле профессионального экскурсовода. Текст на русском языке, 250-300 слов."
    
    return _make_api_request(prompt)

def get_place_reviews(place_name, location):
    """
    Получает обзор отзывов о месте с помощью Perplexity API
    
    Args:
        place_name (str): Название места
        location (str): Местоположение/адрес
        
    Returns:
        str: Обзор отзывов
    """
    prompt = f"Предоставь краткий обзор отзывов о достопримечательности '{place_name}' по адресу {location}. Что обычно отмечают посетители как плюсы и минусы? Какие советы дают для посещения? Ответ на русском языке, до 150 слов."
    
    return _make_api_request(prompt)

def _make_api_request(prompt):
    """
    Отправляет запрос к Perplexity API
    
    Args:
        prompt (str): Текст запроса
        
    Returns:
        str: Ответ от API
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "pplx-7b-online",
        "messages": [
            {"role": "system", "content": "Ты - информативный ассистент по туризму и достопримечательностям. Отвечай детально и точно о местах, их истории и культурном значении. Отвечай только на русском языке."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            print("Ошибка API: Неожиданный формат ответа")
            return "Не удалось получить информацию."
            
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
        return "Не удалось получить информацию из-за ошибки соединения." 