import os
import logging
from datetime import datetime
from aiogram import Router, Bot, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile

from handlers.states import WorkerStates
from handlers.utils import admin_ids, worker_profiles, generate_ref_link, referral_links

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()

@router.message(Command("worker"))
async def cmd_worker(message: types.Message, state: FSMContext, bot: Bot):
    """Обработчик команды /worker для работников"""
    user_id = str(message.from_user.id)
    
    # Создаем клавиатуру с кнопками для работников
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Создать анкету", callback_data="create_profile")
    kb.button(text="🗑 Удалить анкету", callback_data="delete_profile")
    kb.adjust(1)
    
    await message.answer(
        "*👷‍♂️ Панель работника*\n\n"
        "*Выберите действие:*",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "create_profile")
async def process_create_profile(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик создания профиля"""
    user_id = str(callback.from_user.id)
    
    # Проверяем, есть ли уже профиль
    if user_id in worker_profiles:
        await callback.message.edit_text(
            "*⚠️ У вас уже есть анкета*\n\n"
            "*Вы можете удалить существующую и создать новую.*",
            reply_markup=InlineKeyboardBuilder().button(
                text="◀️ Назад", callback_data="back_to_worker"
            ).as_markup(),
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    # Начинаем процесс создания профиля
    await state.set_state(WorkerStates.waiting_for_photo)
    await callback.message.edit_text(
        "*📸 Создание анкеты - Шаг 1/4*\n\n"
        "*Отправьте фотографию профиля:*",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(WorkerStates.waiting_for_photo, F.photo)
async def process_profile_photo(message: types.Message, state: FSMContext):
    """Обработка фото профиля"""
    user_id = str(message.from_user.id)
    
    # Получаем file_id фотографии
    photo_file_id = message.photo[-1].file_id
    
    # Сохраняем в состояние
    await state.update_data(photo_id=photo_file_id)
    
    # Переходим к следующему шагу
    await state.set_state(WorkerStates.waiting_for_name)
    await message.answer(
        "*📝 Создание анкеты - Шаг 2/4*\n\n"
        "*Введите имя для анкеты:*",
        parse_mode="Markdown"
    )

@router.message(WorkerStates.waiting_for_name, F.text)
async def process_profile_name(message: types.Message, state: FSMContext):
    """Обработка имени профиля"""
    user_id = str(message.from_user.id)
    name = message.text
    
    # Сохраняем в состояние
    await state.update_data(name=name)
    
    # Переходим к следующему шагу
    await state.set_state(WorkerStates.waiting_for_followers)
    await message.answer(
        "*👥 Создание анкеты - Шаг 3/4*\n\n"
        "*Введите количество подписчиков:*",
        parse_mode="Markdown"
    )

@router.message(WorkerStates.waiting_for_followers, F.text)
async def process_profile_followers(message: types.Message, state: FSMContext):
    """Обработка количества подписчиков"""
    user_id = str(message.from_user.id)
    followers = message.text
    
    # Сохраняем в состояние
    await state.update_data(followers=followers)
    
    # Переходим к следующему шагу
    await state.set_state(WorkerStates.waiting_for_photos_count)
    await message.answer(
        "*🖼 Создание анкеты - Шаг 4/4*\n\n"
        "*Введите количество фото:*",
        parse_mode="Markdown"
    )

@router.message(WorkerStates.waiting_for_photos_count, F.text)
async def process_profile_photos_count(message: types.Message, state: FSMContext):
    """Обработка количества фото"""
    user_id = str(message.from_user.id)
    photos_count = message.text
    
    # Получаем все данные из состояния
    data = await state.get_data()
    name = data.get("name")
    followers = data.get("followers")
    photo_id = data.get("photo_id")
    
    # Создаем структуру профиля с текущей датой
    now = datetime.now().strftime("%d.%m.%Y")
    
    profile_data = {
        "photo_id": photo_id,
        "name": name,
        "followers": followers,
        "photos_count": photos_count,
        "videos_count": "0",  # По умолчанию
        "date": now,
        "verified": True
    }
    
    # Сохраняем профиль
    worker_profiles[user_id] = profile_data
    
    # Генерируем реферальную ссылку
    ref_link = generate_ref_link(user_id)
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем сообщение с данными профиля и реферальной ссылкой
    await message.answer_photo(
        photo=photo_id,
        caption=(
            f"*✅ Анкета успешно создана!*\n\n"
            f"👩 *Имя:* {name}\n"
            f"🧍 *Подписчики:* {followers}\n"
            f"📷 *Фото:* {photos_count}\n"
            f"🎦 *Видео:* 0\n\n"
            f"🕔 *Дата регистрации:* {now}\n"
            f"📇 *Проверка пройдена:* ✅\n\n"
            f"🔗 *Ваша реферальная ссылка:*\n"
            f"`{ref_link}`\n\n"
            f"_Пользователи, перешедшие по этой ссылке, будут видеть вашу анкету._"
        ),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "delete_profile")
async def process_delete_profile(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик удаления профиля"""
    user_id = str(callback.from_user.id)
    
    # Проверяем наличие профиля
    if user_id not in worker_profiles:
        await callback.message.edit_text(
            "*⚠️ У вас нет активной анкеты*\n\n"
            "*Сначала создайте анкету.*",
            reply_markup=InlineKeyboardBuilder().button(
                text="◀️ Назад", callback_data="back_to_worker"
            ).as_markup(),
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    # Удаляем профиль и все ссылки
    del worker_profiles[user_id]
    
    # Удаляем реферальные ссылки, связанные с этим воркером
    ref_codes_to_delete = []
    for ref_code, worker_id in referral_links.items():
        if worker_id == user_id:
            ref_codes_to_delete.append(ref_code)
    
    for ref_code in ref_codes_to_delete:
        del referral_links[ref_code]
    
    await callback.message.edit_text(
        "*✅ Анкета успешно удалена*\n\n"
        "*Все реферальные ссылки деактивированы.*",
        reply_markup=InlineKeyboardBuilder().button(
            text="◀️ Назад", callback_data="back_to_worker"
        ).as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_worker")
async def back_to_worker(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в меню работника"""
    # Создаем клавиатуру с кнопками для работников
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Создать анкету", callback_data="create_profile")
    kb.button(text="🗑 Удалить анкету", callback_data="delete_profile")
    kb.adjust(1)
    
    await callback.message.edit_text(
        "*👷‍♂️ Панель работника*\n\n"
        "*Выберите действие:*",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

def register_worker_router(dp):
    """Регистрирует роутер в диспетчере"""
    dp.include_router(router) 