import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler, ConversationHandler
from places_api import get_nearby_places, get_place_details
from geopy.distance import geodesic

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния беседы
LOCATION, RADIUS, INTERESTS, PLACE_SELECTION = range(4)

# Категории интересов
INTEREST_CATEGORIES = {
    "Исторические": ["museum", "historic", "landmark"],
    "Природные": ["park", "natural_feature"],
    "Архитектура": ["church", "mosque", "hindu_temple", "synagogue", "point_of_interest"],
    "Культурные": ["art_gallery", "library"],
    "Развлечения": ["amusement_park", "zoo", "aquarium"]
}

# Радиусы поиска
RADIUS_OPTIONS = {
    "100 метров": 100,
    "300 метров": 300,
    "500 метров": 500,
    "1 километр": 1000
}

# Хранилище данных пользователей
user_data_store = {}

def start(update: Update, context: CallbackContext) -> int:
    """Обработчик команды /start"""
    user = update.effective_user
    update.message.reply_text(
        f"Привет, {user.first_name}! Я бот-экскурсовод, который поможет вам найти интересные достопримечательности поблизости. "
        f"Чтобы начать, отправьте мне свою геолокацию, нажав на кнопку ниже.",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Отправить местоположение", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return LOCATION

def location_handler(update: Update, context: CallbackContext) -> int:
    """Обработчик получения геолокации"""
    user_id = update.effective_user.id
    user_location = update.message.location
    
    # Сохраняем данные пользователя
    user_data_store[user_id] = {
        "location": {
            "latitude": user_location.latitude,
            "longitude": user_location.longitude
        }
    }
    
    # Предлагаем выбрать радиус поиска
    keyboard = []
    for radius_name in RADIUS_OPTIONS:
        keyboard.append([InlineKeyboardButton(radius_name, callback_data=f"radius_{RADIUS_OPTIONS[radius_name]}")])
    
    update.message.reply_text(
        "В каком радиусе искать достопримечательности?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return RADIUS

def radius_handler(update: Update, context: CallbackContext) -> int:
    """Обработчик выбора радиуса"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    radius = int(query.data.split('_')[1])
    
    # Сохраняем радиус поиска
    user_data_store[user_id]["radius"] = radius
    
    # Предлагаем выбрать категории интересов
    keyboard = []
    for category in INTEREST_CATEGORIES:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"interest_{category}")])
    keyboard.append([InlineKeyboardButton("Готово", callback_data="interest_done")])
    
    query.edit_message_text(
        "Какие типы достопримечательностей вас интересуют? Выберите один или несколько вариантов:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Инициализируем список интересов
    user_data_store[user_id]["interests"] = []
    
    return INTERESTS

def interest_handler(update: Update, context: CallbackContext) -> int:
    """Обработчик выбора интересов"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "interest_done":
        # Пользователь закончил выбор интересов
        return search_places(update, context)
    
    # Добавляем/удаляем интерес
    interest = data.split('_')[1]
    
    if interest in user_data_store[user_id]["interests"]:
        user_data_store[user_id]["interests"].remove(interest)
    else:
        user_data_store[user_id]["interests"].append(interest)
    
    # Обновляем клавиатуру с отметками выбранных интересов
    keyboard = []
    for category in INTEREST_CATEGORIES:
        text = f"✅ {category}" if category in user_data_store[user_id]["interests"] else category
        keyboard.append([InlineKeyboardButton(text, callback_data=f"interest_{category}")])
    keyboard.append([InlineKeyboardButton("Готово", callback_data="interest_done")])
    
    query.edit_message_text(
        "Какие типы достопримечательностей вас интересуют? Выберите один или несколько вариантов:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return INTERESTS

def search_places(update: Update, context: CallbackContext) -> int:
    """Поиск достопримечательностей на основе выбранных параметров"""
    query = update.callback_query
    user_id = query.from_user.id
    user_data = user_data_store[user_id]
    
    # Преобразуем интересы в типы мест для API
    place_types = []
    for interest in user_data["interests"]:
        place_types.extend(INTEREST_CATEGORIES[interest])
    
    # Если ничего не выбрано, используем все типы
    if not place_types:
        for categories in INTEREST_CATEGORIES.values():
            place_types.extend(categories)
    
    # Поиск мест
    query.edit_message_text("Ищу интересные места поблизости...")
    
    places = get_nearby_places(
        user_data["location"]["latitude"],
        user_data["location"]["longitude"],
        user_data["radius"],
        place_types
    )
    
    if not places:
        query.edit_message_text(
            "К сожалению, я не нашел интересных мест поблизости. Попробуйте увеличить радиус поиска или выбрать другие категории.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать заново", callback_data="restart")]])
        )
        return ConversationHandler.END
    
    # Сохраняем найденные места
    user_data["places"] = places
    
    # Предлагаем выбрать место
    keyboard = []
    for i, place in enumerate(places[:5]):  # Ограничиваем список 5 местами
        distance = geodesic(
            (user_data["location"]["latitude"], user_data["location"]["longitude"]),
            (place["geometry"]["location"]["lat"], place["geometry"]["location"]["lng"])
        ).meters
        
        keyboard.append([
            InlineKeyboardButton(
                f"{place['name']} (~{int(distance)}м)",
                callback_data=f"place_{i}"
            )
        ])
    
    query.edit_message_text(
        "Я нашел несколько интересных мест поблизости. Выберите одно из них:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PLACE_SELECTION

def place_selection_handler(update: Update, context: CallbackContext) -> int:
    """Обработчик выбора места"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    place_index = int(query.data.split('_')[1])
    selected_place = user_data_store[user_id]["places"][place_index]
    
    # Получаем детальную информацию о месте
    query.edit_message_text(f"Загружаю информацию о {selected_place['name']}...")
    
    place_details = get_place_details(selected_place["place_id"])
    user_data_store[user_id]["selected_place"] = place_details
    
    # Формируем информацию о месте
    user_location = user_data_store[user_id]["location"]
    place_location = place_details["geometry"]["location"]
    
    distance = geodesic(
        (user_location["latitude"], user_location["longitude"]),
        (place_location["lat"], place_location["lng"])
    ).meters
    
    address = place_details.get("formatted_address", "Адрес недоступен")
    rating = place_details.get("rating", "Нет оценок")
    
    place_info = (
        f"📍 <b>{place_details['name']}</b>\n\n"
        f"📏 Расстояние: {int(distance)} метров\n"
        f"🏠 Адрес: {address}\n"
        f"⭐ Рейтинг: {rating}\n\n"
    )
    
    if "photos" in place_details:
        photo_reference = place_details["photos"][0]["photo_reference"]
        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=600&photoreference={photo_reference}&key={os.getenv('GOOGLE_PLACES_API_KEY')}"
        
        # Отправляем фото и информацию
        context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=photo_url,
            caption=place_info,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Проложить маршрут", callback_data=f"route_{place_index}")],
                [InlineKeyboardButton("Мини-экскурсия", callback_data=f"excursion_{place_index}")],
                [InlineKeyboardButton("Выбрать другое место", callback_data="back_to_places")]
            ])
        )
    else:
        # Отправляем только информацию
        query.edit_message_text(
            place_info,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Проложить маршрут", callback_data=f"route_{place_index}")],
                [InlineKeyboardButton("Мини-экскурсия", callback_data=f"excursion_{place_index}")],
                [InlineKeyboardButton("Выбрать другое место", callback_data="back_to_places")]
            ])
        )
    
    return PLACE_SELECTION

def route_handler(update: Update, context: CallbackContext) -> int:
    """Обработчик запроса на построение маршрута"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    place_index = int(query.data.split('_')[1])
    selected_place = user_data_store[user_id]["places"][place_index]
    
    user_location = user_data_store[user_id]["location"]
    place_location = selected_place["geometry"]["location"]
    
    # Формируем ссылку на Google Maps
    maps_url = (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={user_location['latitude']},{user_location['longitude']}"
        f"&destination={place_location['lat']},{place_location['lng']}"
        f"&travelmode=walking"
    )
    
    query.edit_message_text(
        f"Маршрут до {selected_place['name']} построен! Нажмите на кнопку ниже, чтобы открыть его в Google Maps:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Открыть маршрут", url=maps_url)],
            [InlineKeyboardButton("Назад", callback_data=f"place_{place_index}")]
        ])
    )
    
    return PLACE_SELECTION

def excursion_handler(update: Update, context: CallbackContext) -> int:
    """Обработчик запроса на мини-экскурсию"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    place_index = int(query.data.split('_')[1])
    selected_place = user_data_store[user_id]["selected_place"]
    
    # Здесь можно добавить генерацию экскурсии на основе информации о месте
    # В реальном проекте можно использовать API для получения исторических данных
    # или интегрировать ChatGPT для генерации интересного текста
    
    excursion_text = (
        f"<b>Мини-экскурсия по {selected_place['name']}</b>\n\n"
        f"Это место имеет большую историческую и культурную ценность. "
        f"Оно было основано много лет назад и с тех пор привлекает множество туристов. "
        f"Особенно интересны архитектурные особенности и история развития этого места.\n\n"
        f"В реальной версии здесь будет более подробная и точная информация о выбранном месте, "
        f"собранная из различных источников или сгенерированная с помощью AI."
    )
    
    query.edit_message_text(
        excursion_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Назад", callback_data=f"place_{place_index}")]
        ])
    )
    
    return PLACE_SELECTION

def back_to_places(update: Update, context: CallbackContext) -> int:
    """Возврат к списку мест"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    user_data = user_data_store[user_id]
    
    # Предлагаем выбрать место
    keyboard = []
    for i, place in enumerate(user_data["places"][:5]):
        distance = geodesic(
            (user_data["location"]["latitude"], user_data["location"]["longitude"]),
            (place["geometry"]["location"]["lat"], place["geometry"]["location"]["lng"])
        ).meters
        
        keyboard.append([
            InlineKeyboardButton(
                f"{place['name']} (~{int(distance)}м)",
                callback_data=f"place_{i}"
            )
        ])
    
    query.edit_message_text(
        "Выберите одно из мест:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PLACE_SELECTION

def restart(update: Update, context: CallbackContext) -> int:
    """Перезапуск бота"""
    query = update.callback_query
    query.answer()
    
    return start(update, context)

def cancel(update: Update, context: CallbackContext) -> int:
    """Обработчик команды /cancel"""
    update.message.reply_text(
        "Поиск отменен. Чтобы начать заново, отправьте /start.",
        reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True)
    )
    
    return ConversationHandler.END

def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help"""
    update.message.reply_text(
        "Я бот-экскурсовод, который поможет вам найти интересные достопримечательности рядом с вами.\n\n"
        "Доступные команды:\n"
        "/start - Начать поиск достопримечательностей\n"
        "/cancel - Отменить текущий поиск\n"
        "/help - Показать эту справку"
    )

def main() -> None:
    """Запуск бота"""
    # Получаем токен из переменных окружения
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("Не указан токен бота. Проверьте файл .env")
        return
    
    # Создаем Updater и передаем ему токен бота
    updater = Updater(token)
    
    # Получаем диспетчер для регистрации обработчиков
    dispatcher = updater.dispatcher
    
    # Создаем обработчик разговора
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LOCATION: [MessageHandler(Filters.location, location_handler)],
            RADIUS: [CallbackQueryHandler(radius_handler, pattern=r"^radius_")],
            INTERESTS: [CallbackQueryHandler(interest_handler, pattern=r"^interest_")],
            PLACE_SELECTION: [
                CallbackQueryHandler(place_selection_handler, pattern=r"^place_"),
                CallbackQueryHandler(route_handler, pattern=r"^route_"),
                CallbackQueryHandler(excursion_handler, pattern=r"^excursion_"),
                CallbackQueryHandler(back_to_places, pattern=r"^back_to_places$"),
                CallbackQueryHandler(restart, pattern=r"^restart$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Регистрируем обработчик разговора
    dispatcher.add_handler(conv_handler)
    
    # Регистрируем обработчик команды help
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    # Запускаем бота
    updater.start_polling()
    logger.info("Бот запущен")
    
    # Работаем до нажатия Ctrl-C
    updater.idle()

if __name__ == "__main__":
    main() 