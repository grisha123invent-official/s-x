import os
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# API-ключ
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

# Базовые URL для API-запросов
NEARBY_PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

def get_nearby_places(latitude, longitude, radius, types=None, limit=20):
    """
    Получает список ближайших достопримечательностей из Google Places API
    
    Args:
        latitude (float): Широта местоположения пользователя
        longitude (float): Долгота местоположения пользователя
        radius (int): Радиус поиска в метрах
        types (list): Список типов мест для поиска
        limit (int): Максимальное количество результатов
        
    Returns:
        list: Список найденных мест
    """
    params = {
        "location": f"{latitude},{longitude}",
        "radius": radius,
        "key": API_KEY,
        "language": "ru"
    }
    
    # Добавляем типы мест, если они указаны
    if types:
        # Удаляем дубликаты из списка типов
        unique_types = list(set(types))
        params["type"] = "|".join(unique_types)
    
    try:
        response = requests.get(NEARBY_PLACES_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "OK" and data["status"] != "ZERO_RESULTS":
            print(f"Ошибка API: {data['status']}")
            return []
        
        # Фильтруем результаты, оставляя только места с рейтингом и названием
        places = []
        for place in data.get("results", []):
            if "name" in place:
                places.append(place)
            
            # Ограничиваем количество результатов
            if len(places) >= limit:
                break
                
        return places
    
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
        return []

def get_place_details(place_id):
    """
    Получает подробную информацию о месте из Google Places API
    
    Args:
        place_id (str): Идентификатор места
        
    Returns:
        dict: Подробная информация о месте
    """
    params = {
        "place_id": place_id,
        "key": API_KEY,
        "language": "ru",
        "fields": "name,formatted_address,rating,photos,geometry,opening_hours,website,review,price_level,formatted_phone_number"
    }
    
    try:
        response = requests.get(PLACE_DETAILS_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "OK":
            print(f"Ошибка API: {data['status']}")
            return {}
        
        return data["result"]
    
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
        return {} 