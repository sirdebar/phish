import asyncio
import logging
import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from handlers.start import register_start_router
from handlers.auth import register_auth_router
from handlers.admin import register_admin_router
from handlers.worker import register_worker_router
from handlers.utils import admin_ids, bot_username

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
logger.info("Загрузка переменных окружения из config/.env")
load_dotenv('config/.env')

# Проверяем наличие всех необходимых переменных окружения
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')

if not api_id or not api_hash or not bot_token:
    logger.error("Не все переменные окружения настроены. Проверьте .env файл.")
    if not api_id:
        logger.error("API_ID не задан")
    if not api_hash:
        logger.error("API_HASH не задан")
    if not bot_token:
        logger.error("BOT_TOKEN не задан")
    exit(1)

# Проверка корректности API_ID (должен быть целым числом)
try:
    int(api_id)
    logger.info(f"API_ID: {api_id} (целое число)")
except ValueError:
    logger.error(f"API_ID должен быть целым числом: {api_id}")
    exit(1)

logger.info(f"API_HASH: {api_hash[:4]}...{api_hash[-4:]}")
logger.info(f"BOT_TOKEN: {bot_token[:4]}...{bot_token[-4:]}")

# Получаем имя бота
try:
    response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe")
    if response.status_code == 200:
        data = response.json()
        if data["ok"]:
            from handlers.utils import bot_username as utils_bot_username
            bot_name = data["result"]["username"]
            globals()["bot_username"] = bot_name
            if 'utils_bot_username' in globals():
                utils_bot_username = bot_name
            logger.info(f"Имя бота: @{bot_name}")
        else:
            logger.error(f"Ошибка при получении имени бота: {data}")
    else:
        logger.error(f"Ошибка HTTP при запросе к API: {response.status_code}")
except Exception as e:
    logger.error(f"Ошибка при определении имени бота: {str(e)}")

# Загружаем список ID администраторов из переменной окружения
admin_list = os.getenv('ADMIN_IDS', '').split(',')
for admin_id in admin_list:
    if admin_id and admin_id.strip():
        admin_ids.append(admin_id.strip())

logger.info(f"Админы: {admin_ids}")

# Инициализация бота и диспетчера
bot = Bot(token=bot_token)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрация роутеров
async def main():
    logger.info("Запуск бота...")
    
    # Регистрация обработчиков
    register_start_router(dp)
    register_auth_router(dp)
    register_admin_router(dp)
    register_worker_router(dp)
    
    # Создаем директории для сессий и изображений, если они не существуют
    os.makedirs('sessions', exist_ok=True)
    os.makedirs('images', exist_ok=True)
    
    # Проверка наличия файла изображения для стартового экрана
    start_image_path = "images/start.png"
    if not os.path.exists(start_image_path):
        logger.warning(f"Изображение для стартового экрана не найдено: {start_image_path}")
        logger.warning("Бот будет работать без изображения для стартового экрана")
    
    # Отправка сообщения всем администраторам о запуске бота
    try:
        start_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    admin_id,
                    f"*🤖 Бот запущен*\n\n"
                    f"*Время запуска:* {start_time}\n\n"
                    f"*Используйте команду /start для входа в админ-панель*",
                    parse_mode="Markdown"
                )
                logger.info(f"Отправлено уведомление о запуске бота администратору {admin_id}")
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений администраторам: {str(e)}")
    
    # Запуск бота
    logger.info("Бот запущен и готов к работе.")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен!")
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True) 