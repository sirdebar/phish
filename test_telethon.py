import os
import sys
import asyncio
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError

async def main():
    # Загружаем переменные окружения
    load_dotenv('config/.env')
    
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    
    if not api_id or not api_hash:
        print("Ошибка: API_ID или API_HASH не найдены в .env файле")
        return
    
    print(f"API_ID: {api_id}")
    print(f"API_HASH: {api_hash}")
    
    # Проверяем передан ли номер телефона как аргумент
    if len(sys.argv) != 2:
        print("Использование: python test_telethon.py +79XXXXXXXXX")
        return
    
    phone = sys.argv[1]
    print(f"Номер телефона: {phone}")
    
    # Создаем временный клиент для теста
    client = TelegramClient('test_session', int(api_id), api_hash)
    
    try:
        print("Подключение к Telegram...")
        await client.connect()
        
        print(f"Отправка запроса кода на номер {phone}...")
        try:
            result = await client.send_code_request(phone)
            print(f"Код успешно отправлен!")
            print(f"phone_code_hash: {result.phone_code_hash}")
            
            # Просим ввести код
            code = input("Введите полученный код: ")
            
            # Пытаемся войти
            print(f"Вход с кодом: {code}")
            await client.sign_in(phone, code, phone_code_hash=result.phone_code_hash)
            
            print("Авторизация успешна!")
            if await client.is_user_authorized():
                me = await client.get_me()
                print(f"Вы вошли как: {me.first_name} (ID: {me.id})")
            
        except FloodWaitError as e:
            print(f"Ошибка FloodWaitError: нужно подождать {e.seconds} секунд")
        except Exception as e:
            print(f"Ошибка при отправке кода: {str(e)}")
    
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
    
    finally:
        await client.disconnect()
        print("Отключено от Telegram")

if __name__ == "__main__":
    asyncio.run(main()) 