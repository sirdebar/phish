import os
import asyncio
import logging
from aiogram import Bot
from datetime import datetime

# Настройка логирования
logger = logging.getLogger(__name__)

# Словарь для отслеживания времени начала процесса авторизации
auth_start_times = {}
# Словарь для хранения временных данных пользователей (код авторизации)
user_auth_data = {}
# Список админов (будет загружен из .env)
admin_ids = []
# Флаг для уведомлений админов
admin_notifications = True

# Таймаут авторизации (в секундах)
AUTH_TIMEOUT = 300  # 5 минут

async def check_auth_timeout(user_id, bot):
    """Проверяет таймаут авторизации и отменяет процесс, если время вышло"""
    await asyncio.sleep(AUTH_TIMEOUT)
    if user_id in auth_start_times:
        now = datetime.now()
        start_time = auth_start_times[user_id]
        if (now - start_time).total_seconds() >= AUTH_TIMEOUT:
            # Удаляем данные авторизации
            if user_id in auth_start_times:
                del auth_start_times[user_id]
            if user_id in user_auth_data:
                del user_auth_data[user_id]
            
            # Отправляем сообщение пользователю
            await bot.send_message(
                user_id, 
                "*⚠️ Время ожидания истекло*\n\n*Процесс авторизации отменен. Для повторной попытки используйте команду /start*",
                parse_mode="Markdown"
            )

def format_with_emoji(text):
    """Делает текст жирным и добавляет тематические эмодзи (без переизбытка)"""
    emoji_text = text
    
    # Добавляем ключевые эмодзи (но более сдержанно)
    emoji_text = emoji_text.replace("OnlyFans Premium", "🔥 *OnlyFans Premium*")
    emoji_text = emoji_text.replace("10.000 девушек", "*10.000+* девушек 👩‍🦰")
    emoji_text = emoji_text.replace("море откровенных анкет", "море откровенных анкет 📸")
    emoji_text = emoji_text.replace("зарегистрироваться", "зарегистрироваться 📝")
    emoji_text = emoji_text.replace("ВНИМАНИЕ:", "⚠️ *ВНИМАНИЕ:*")
    emoji_text = emoji_text.replace("перезапустите его", "перезапустите его 🔄")
    
    # Сделать весь текст жирным
    lines = emoji_text.split('\n')
    for i, line in enumerate(lines):
        if line.strip() and not (line.strip().startswith('*') and line.strip().endswith('*')):
            # Проверяем каждое слово в строке
            words = line.split()
            for j, word in enumerate(words):
                if '*' not in word:
                    words[j] = f"*{word}*"
            lines[i] = ' '.join(words)
    
    return '\n'.join(lines) 