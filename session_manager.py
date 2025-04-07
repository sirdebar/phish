#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from telethon import functions, types

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Настройки API из .env файла
from dotenv import load_dotenv
load_dotenv('config/.env')

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')

# Цвета для терминала
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

async def get_session_info(session_path):
    """Получить базовую информацию о сессии"""
    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"{Colors.RED}[!] Пользователь не авторизован в этой сессии{Colors.ENDC}")
            await client.disconnect()
            return None
        
        # Получаем информацию о пользователе
        me = await client.get_me()
        print(f"{Colors.GREEN}[+] Успешное подключение к сессии: {me.first_name} {me.last_name if me.last_name else ''} (@{me.username if me.username else 'без юзернейма'}){Colors.ENDC}")
        print(f"{Colors.BLUE}[i] ID пользователя: {me.id}{Colors.ENDC}")
        
        # Получаем диалоги
        result = await client(GetDialogsRequest(
            offset_date=None,
            offset_id=0,
            offset_peer=InputPeerEmpty(),
            limit=50,
            hash=0
        ))
        
        dialogs = result.dialogs
        print(f"{Colors.BLUE}[i] Количество диалогов: {len(dialogs)}{Colors.ENDC}")
        
        # Закрываем соединение
        await client.disconnect()
        return me
    
    except Exception as e:
        print(f"{Colors.RED}[!] Ошибка при работе с сессией: {str(e)}{Colors.ENDC}")
        return None

async def send_message(session_path, target, message):
    """Отправить сообщение пользователю или в группу"""
    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"{Colors.RED}[!] Пользователь не авторизован в этой сессии{Colors.ENDC}")
            await client.disconnect()
            return False
        
        # Отправляем сообщение
        await client.send_message(target, message)
        print(f"{Colors.GREEN}[+] Сообщение успешно отправлено пользователю {target}{Colors.ENDC}")
        
        # Закрываем соединение
        await client.disconnect()
        return True
    
    except Exception as e:
        print(f"{Colors.RED}[!] Ошибка при отправке сообщения: {str(e)}{Colors.ENDC}")
        return False

async def browse_dialogs(session_path):
    """Просмотр последних диалогов пользователя"""
    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"{Colors.RED}[!] Пользователь не авторизован в этой сессии{Colors.ENDC}")
            await client.disconnect()
            return False
        
        # Получаем диалоги
        dialogs = await client.get_dialogs(limit=50)
        
        print(f"{Colors.BLUE}[i] Последние диалоги:{Colors.ENDC}")
        for i, dialog in enumerate(dialogs, 1):
            entity_type = "Канал" if dialog.is_channel else "Группа" if dialog.is_group else "Пользователь"
            print(f"{Colors.YELLOW}{i}. {dialog.name} - {entity_type}{Colors.ENDC}")
            
            # Получаем последнее сообщение
            messages = await client.get_messages(dialog.entity, limit=1)
            if messages and messages[0].message:
                preview = messages[0].message[:50] + "..." if len(messages[0].message) > 50 else messages[0].message
                print(f"   Последнее сообщение: {preview}")
            
            print("")  # Пустая строка для разделения
        
        # Закрываем соединение
        await client.disconnect()
        return True
    
    except Exception as e:
        print(f"{Colors.RED}[!] Ошибка при получении диалогов: {str(e)}{Colors.ENDC}")
        return False

async def read_messages(session_path, chat_id, limit=10):
    """Прочитать последние сообщения из конкретного чата"""
    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"{Colors.RED}[!] Пользователь не авторизован в этой сессии{Colors.ENDC}")
            await client.disconnect()
            return False
        
        # Получаем сообщения
        messages = await client.get_messages(chat_id, limit=limit)
        
        print(f"{Colors.BLUE}[i] Последние {len(messages)} сообщений из чата {chat_id}:{Colors.ENDC}")
        for i, message in enumerate(reversed(messages), 1):
            sender = message.sender_id
            sender_info = ""
            
            if sender:
                try:
                    sender_entity = await client.get_entity(sender)
                    sender_info = f"{sender_entity.first_name} {sender_entity.last_name if hasattr(sender_entity, 'last_name') and sender_entity.last_name else ''}"
                except:
                    sender_info = f"ID: {sender}"
            
            msg_text = message.message if message.message else "[Медиа или служебное сообщение]"
            print(f"{Colors.YELLOW}{i}. От: {sender_info}{Colors.ENDC}")
            print(f"   {msg_text}")
            print("")  # Пустая строка для разделения
        
        # Закрываем соединение
        await client.disconnect()
        return True
    
    except Exception as e:
        print(f"{Colors.RED}[!] Ошибка при чтении сообщений: {str(e)}{Colors.ENDC}")
        return False

async def list_sessions():
    """Вывести список всех доступных сессий"""
    sessions_dir = "sessions"
    
    if not os.path.exists(sessions_dir):
        print(f"{Colors.RED}[!] Директория с сессиями не найдена{Colors.ENDC}")
        return []
    
    session_files = [f for f in os.listdir(sessions_dir) if f.endswith(".session")]
    
    if not session_files:
        print(f"{Colors.YELLOW}[!] Сессии не найдены{Colors.ENDC}")
        return []
    
    print(f"{Colors.BLUE}[i] Доступные сессии ({len(session_files)}):{Colors.ENDC}")
    sessions = []
    
    for i, session_file in enumerate(session_files, 1):
        session_name = session_file[:-8]  # Убираем расширение .session
        sessions.append(session_name)
        print(f"{Colors.YELLOW}{i}. {session_name}{Colors.ENDC}")
    
    return sessions

async def start_interactive_session(session_path):
    """Запустить интерактивную сессию для работы с аккаунтом"""
    user = await get_session_info(session_path)
    
    if not user:
        return
    
    while True:
        print(f"\n{Colors.BOLD}Меню работы с сессией {user.first_name}:{Colors.ENDC}")
        print(f"{Colors.BLUE}1. Просмотреть диалоги{Colors.ENDC}")
        print(f"{Colors.BLUE}2. Прочитать сообщения из чата{Colors.ENDC}")
        print(f"{Colors.BLUE}3. Отправить сообщение{Colors.ENDC}")
        print(f"{Colors.BLUE}4. Просмотреть информацию о пользователе{Colors.ENDC}")
        print(f"{Colors.BLUE}5. Выйти{Colors.ENDC}")
        
        choice = input(f"{Colors.BOLD}Выберите действие (1-5): {Colors.ENDC}")
        
        if choice == '1':
            await browse_dialogs(session_path)
        elif choice == '2':
            chat_id = input(f"{Colors.BOLD}Введите ID чата или юзернейм: {Colors.ENDC}")
            limit = input(f"{Colors.BOLD}Сколько сообщений показать (Enter для 10): {Colors.ENDC}")
            limit = int(limit) if limit.isdigit() else 10
            await read_messages(session_path, chat_id, limit)
        elif choice == '3':
            target = input(f"{Colors.BOLD}Введите ID пользователя или юзернейм: {Colors.ENDC}")
            message = input(f"{Colors.BOLD}Введите сообщение: {Colors.ENDC}")
            await send_message(session_path, target, message)
        elif choice == '4':
            # Покажем детальную информацию о пользователе
            client = TelegramClient(session_path, API_ID, API_HASH)
            try:
                await client.connect()
                if await client.is_user_authorized():
                    me = await client.get_me()
                    print(f"\n{Colors.GREEN}Информация о пользователе:{Colors.ENDC}")
                    print(f"{Colors.BLUE}ID: {me.id}{Colors.ENDC}")
                    print(f"{Colors.BLUE}Имя: {me.first_name}{Colors.ENDC}")
                    print(f"{Colors.BLUE}Фамилия: {me.last_name if me.last_name else 'Не указана'}{Colors.ENDC}")
                    print(f"{Colors.BLUE}Юзернейм: @{me.username if me.username else 'Не указан'}{Colors.ENDC}")
                    print(f"{Colors.BLUE}Телефон: {me.phone if me.phone else 'Не указан'}{Colors.ENDC}")
                    print(f"{Colors.BLUE}Премиум: {'Да' if me.premium else 'Нет'}{Colors.ENDC}")
                    
                    # Получаем информацию о диалогах
                    dialogs = await client.get_dialogs(limit=None)
                    total_dialogs = len(dialogs)
                    
                    # Считаем типы диалогов
                    channels = 0
                    groups = 0
                    users = 0
                    for dialog in dialogs:
                        if dialog.is_channel:
                            channels += 1
                        elif dialog.is_group:
                            groups += 1
                        else:
                            users += 1
                    
                    print(f"{Colors.BLUE}Всего диалогов: {total_dialogs}{Colors.ENDC}")
                    print(f"{Colors.BLUE}- Каналов: {channels}{Colors.ENDC}")
                    print(f"{Colors.BLUE}- Групп: {groups}{Colors.ENDC}")
                    print(f"{Colors.BLUE}- Личных чатов: {users}{Colors.ENDC}")
                else:
                    print(f"{Colors.RED}[!] Пользователь не авторизован{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}[!] Ошибка при получении информации: {str(e)}{Colors.ENDC}")
            finally:
                await client.disconnect()
        elif choice == '5':
            print(f"{Colors.GREEN}[+] Выход из сессии{Colors.ENDC}")
            break
        else:
            print(f"{Colors.RED}[!] Неверный выбор{Colors.ENDC}")

async def main():
    print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{' ' * 15}МЕНЕДЖЕР СЕССИЙ TELEGRAM{' ' * 15}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
    
    sessions = await list_sessions()
    
    if not sessions:
        print(f"{Colors.RED}[!] Нет доступных сессий для работы{Colors.ENDC}")
        return
    
    while True:
        print(f"\n{Colors.BOLD}Главное меню:{Colors.ENDC}")
        print(f"{Colors.BLUE}1. Выбрать сессию{Colors.ENDC}")
        print(f"{Colors.BLUE}2. Обновить список сессий{Colors.ENDC}")
        print(f"{Colors.BLUE}3. Выйти{Colors.ENDC}")
        
        choice = input(f"{Colors.BOLD}Выберите действие (1-3): {Colors.ENDC}")
        
        if choice == '1':
            session_idx = input(f"{Colors.BOLD}Введите номер сессии (1-{len(sessions)}): {Colors.ENDC}")
            
            if not session_idx.isdigit() or int(session_idx) < 1 or int(session_idx) > len(sessions):
                print(f"{Colors.RED}[!] Неверный номер сессии{Colors.ENDC}")
                continue
            
            session_path = f"sessions/{sessions[int(session_idx) - 1]}"
            await start_interactive_session(session_path)
        elif choice == '2':
            sessions = await list_sessions()
        elif choice == '3':
            print(f"{Colors.GREEN}[+] Выход из программы{Colors.ENDC}")
            break
        else:
            print(f"{Colors.RED}[!] Неверный выбор{Colors.ENDC}")

if __name__ == "__main__":
    asyncio.run(main()) 