import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Загрузка переменных окружения
load_dotenv('config/.env')

# Функция для создания и показа клавиатуры
async def test_keyboard():
    # Получаем токен бота
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("Ошибка: BOT_TOKEN не найден в .env файле")
        return
    
    # Создаем экземпляр бота и диспетчера
    bot = Bot(token=bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Обработчик команды /start
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        # Создаем клавиатуру для ввода кода
        keyboard = ReplyKeyboardBuilder()
        
        # Добавляем цифры от 1 до 9
        for i in range(1, 10):
            keyboard.button(text=str(i))
        
        # Добавляем 0 и кнопку удаления
        keyboard.button(text="0")
        keyboard.button(text="⌫")
        
        # Располагаем кнопки в сетке 3x4
        keyboard.adjust(3, 3, 3, 2)
        
        await message.answer(
            "Клавиатура для ввода кода. Нажмите на цифры для проверки.",
            reply_markup=keyboard.as_markup(resize_keyboard=True)
        )
    
    # Обработчик текстовых сообщений
    @dp.message()
    async def handle_text(message: types.Message):
        if message.text == "⌫":
            await message.answer("Нажата кнопка удаления")
        elif message.text.isdigit() and len(message.text) == 1:
            await message.answer(f"Введена цифра: {message.text}")
        else:
            await message.answer("Введите цифру или нажмите кнопку удаления")
    
    try:
        # Запускаем бота
        print("Запускаем тестового бота. Отправьте /start для проверки клавиатуры.")
        print("Для остановки нажмите Ctrl+C")
        await dp.start_polling(bot)
    finally:
        print("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(test_keyboard()) 