from aiogram.fsm.state import State, StatesGroup

class AuthStates(StatesGroup):
    """Состояния для процесса авторизации"""
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_2fa = State()
    
class AdminStates(StatesGroup):
    """Состояния для админ-панели"""
    admin_menu = State() 