from aiogram.fsm.state import State, StatesGroup

class AuthStates(StatesGroup):
    """Состояния для процесса авторизации"""
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_2fa = State()
    
class AdminStates(StatesGroup):
    """Состояния для админ-панели"""
    admin_menu = State() 

class WorkerStates(StatesGroup):
    """Состояния для работников"""
    creating_profile = State()
    waiting_for_photo = State()
    waiting_for_name = State()
    waiting_for_followers = State()
    waiting_for_photos_count = State()
    waiting_for_videos_count = State() 