import os
from aiogram import Router, Bot, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.states import AdminStates
from handlers.utils import admin_ids, format_with_emoji

# Создаем роутер
router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext, bot: Bot):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь админом
    if str(user_id) in admin_ids:
        await show_admin_panel(message, state)
        return
    
    # Для обычного пользователя показываем приветствие
    await state.clear()
    
    # Формируем приветственное сообщение с эмодзи (более сдержанно)
    welcome_text = f"""
Пользователь: {message.from_user.full_name}

OnlyFans Premium - У нас вы найдете более 10.000 девушек и море откровенных анкет

Для начала просмотра необходимо зарегистрироваться п кнопке снизу.

ВНИМАНИЕ: Если бот не прислал вам код, перезапустите его командой /start
"""
    
    # Применяем форматирование с эмодзи
    formatted_text = format_with_emoji(welcome_text)
    
    # Создаем инлайн клавиатуру
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Зарегистрироваться", callback_data="register")
    
    # Проверяем наличие изображения
    image_path = "images/start.png"
    if os.path.exists(image_path):
        # Отправляем изображение с текстом и кнопкой
        with open(image_path, "rb") as photo_file:
            # Правильно используем InputFile для отправки фото
            await message.answer_photo(
                photo=types.BufferedInputFile(
                    photo_file.read(),
                    filename="start.png"
                ),
                caption=formatted_text,
                reply_markup=kb.as_markup(),
                parse_mode="Markdown"
            )
    else:
        # Если изображения нет, отправляем только текст с кнопкой
        await message.answer(
            formatted_text,
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )

async def show_admin_panel(message: types.Message, state: FSMContext):
    """Показывает панель администратора"""
    from handlers.utils import admin_notifications
    
    await state.set_state(AdminStates.admin_menu)
    
    # Создаем клавиатуру админа
    kb = InlineKeyboardBuilder()
    kb.button(text="📁 Все сессии", callback_data="all_sessions")
    
    # Кнопка включения/отключения уведомлений
    notification_text = "🔕 Отключить уведомления" if admin_notifications else "🔔 Включить уведомления"
    kb.button(text=notification_text, callback_data="toggle_notifications")
    
    # Располагаем кнопки в столбик
    kb.adjust(1)
    
    await message.answer(
        "*👑 Панель администратора*\n\n*Выберите действие:*",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

def register_start_router(dp):
    """Регистрирует роутер в диспетчере"""
    dp.include_router(router) 