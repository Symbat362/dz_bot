from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_submission = State()
