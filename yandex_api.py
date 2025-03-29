import os
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# API-ключ
API_KEY = os.getenv("YANDEX_API_KEY")

# Базовые URL для API-запросов
GEOCODE_URL = "https://geocode-maps.yandex.ru/1.x/"
SEARCH_URL = "https://search-maps.yandex.ru/v1/"
STATIC_MAPS_URL = "https://static-maps.yandex.ru/1.x/"

def get_nearby_places(latitude, longitude, radius, types=None, limit=20):
    """
    Получает список ближайших достопримечательностей через Яндекс API
    
    Args:
        latitude (float): Широта местоположения пользователя
        longitude (float): Долгота местоположения пользователя
        radius (int): Радиус поиска в метрах
        types (list): Список типов мест для поиска
        limit (int): Максимальное количество результатов
        
    Returns:
        list: Список найденных мест
    """
    # Формируем текст запроса на основе типов
    text = "достопримечательность"
    if types:
        if "museum" in types or "historic" in types or "landmark" in types:
            text = "музей|памятник|достопримечательность"
        elif "park" in types or "natural_feature" in types:
            text = "парк|сад|природная достопримечательность"
        elif "church" in types or "mosque" in types or "hindu_temple" in types or "synagogue" in types:
            text = "храм|церковь|мечеть|синагога"
        elif "art_gallery" in types or "library" in types:
            text = "галерея|библиотека|выставка"
        elif "amusement_park" in types or "zoo" in types or "aquarium" in types:
            text = "зоопарк|аквариум|парк развлечений"
    
    params = {
        "apikey": API_KEY,
        "text": text,
        "lang": "ru_RU",
        "ll": f"{longitude},{latitude}",
        "spn": f"{radius/100000},{radius/100000}",
        "results": limit,
        "type": "biz",
    }
    
    try:
        response = requests.get(SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "features" not in data:
            print("Ошибка API: Нет результатов")
            return []
        
        # Преобразуем формат данных для совместимости с существующим кодом
        places = []
        for feature in data["features"]:
            properties = feature["properties"]
            geometry = feature["geometry"]
            
            place = {
                "place_id": properties["CompanyMetaData"].get("id", ""),
                "name": properties["name"],
                "geometry": {
                    "location": {
                        "lat": geometry["coordinates"][1],
                        "lng": geometry["coordinates"][0]
                    }
                }
            }
            
            # Добавляем адрес, если есть
            if "address" in properties["CompanyMetaData"]:
                place["vicinity"] = properties["CompanyMetaData"]["address"]
            
            places.append(place)
            
        return places
    
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
        return []

def get_place_details(place_id):
    """
    Получает подробную информацию о месте через Яндекс API
    
    Args:
        place_id (str): Идентификатор места
        
    Returns:
        dict: Подробная информация о месте
    """
    # В Яндекс API нет отдельного метода для получения детальной информации по ID объекта
    # Поэтому используем поиск по ID
    params = {
        "apikey": API_KEY,
        "text": place_id,
        "lang": "ru_RU",
        "results": 1,
        "type": "biz",
    }
    
    try:
        response = requests.get(SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "features" not in data or len(data["features"]) == 0:
            print(f"Ошибка API: Место с ID {place_id} не найдено")
            return {}
        
        feature = data["features"][0]
        properties = feature["properties"]
        geometry = feature["geometry"]
        metadata = properties.get("CompanyMetaData", {})
        
        # Формируем результат в формате, совместимом с текущим кодом
        result = {
            "place_id": place_id,
            "name": properties["name"],
            "geometry": {
                "location": {
                    "lat": geometry["coordinates"][1],
                    "lng": geometry["coordinates"][0]
                }
            }
        }
        
        # Добавляем адрес
        if "address" in metadata:
            result["formatted_address"] = metadata["address"]
        
        # Добавляем телефон
        if "Phones" in metadata and metadata["Phones"]:
            result["formatted_phone_number"] = metadata["Phones"][0].get("formatted", "")
        
        # Добавляем URL
        if "url" in metadata:
            result["website"] = metadata["url"]
        
        # Добавляем время работы
        if "Hours" in metadata:
            result["opening_hours"] = {
                "weekday_text": metadata["Hours"].get("text", "")
            }
        
        # Добавляем фото (используем статическую карту как превью)
        result["photos"] = [{
            "photo_reference": f"{geometry['coordinates'][1]},{geometry['coordinates'][0]}"
        }]
        
        return result
    
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к API: {e}")
        return {}

def get_static_map_url(latitude, longitude, zoom=16):
    """
    Возвращает URL статической карты Яндекса
    
    Args:
        latitude (float): Широта
        longitude (float): Долгота
        zoom (int): Уровень приближения
        
    Returns:
        str: URL статической карты
    """
    return f"{STATIC_MAPS_URL}?ll={longitude},{latitude}&z={zoom}&l=map&pt={longitude},{latitude},pm2rdm&apikey={API_KEY}"

def get_route_url(from_lat, from_lng, to_lat, to_lng):
    """
    Создает URL для построения маршрута в Яндекс Картах
    
    Args:
        from_lat (float): Широта начальной точки
        from_lng (float): Долгота начальной точки
        to_lat (float): Широта конечной точки
        to_lng (float): Долгота конечной точки
        
    Returns:
        str: URL маршрута
    """
    return f"https://yandex.ru/maps/?rtext={from_lat},{from_lng}~{to_lat},{to_lng}&rtt=pd" 