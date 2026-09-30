from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_student_name = State()
    waiting_for_task_content = State()
    waiting_for_student_selection = State()
    waiting_for_task_description = State()
    waiting_for_deadline = State()
