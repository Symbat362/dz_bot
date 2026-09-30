from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database import requests as rq
from states.user import UserStates
from config import settings
from datetime import datetime

router = Router()

user_main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Менің тапсырмаларым / Мои задания")]
], resize_keyboard=True)

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user = await rq.get_user_by_tg_id(message.from_user.id)
    if user:
        await message.answer(f"Қош келдіңіз, {user.name}! / Добро пожаловать, {user.name}!", reply_markup=user_main_kb)
        await show_my_tasks(message, user.id)
    else:
        await message.answer("Қош келдіңіз! Жеке кодыңызд еңгізіңіз / Введите ваш код:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(UserStates.waiting_for_code)

@router.message(UserStates.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    if not getattr(message, "text", None):
        await message.answer("Пожалуйста, отправьте код в текстовом сообщении (только цифры). / Пожалуйста, введите код текстом.")
        return

    code = message.text.strip()
    user = await rq.get_user_by_code(code)
    if user:
        if user.telegram_id:
             await message.answer("Бұл код бос емес / Этот код уже используется.")
        else:
            await rq.attach_user_tg_id(code, message.from_user.id)
            await message.answer(f"{user.name}, код қабылданды! Енді күтіңіз. / Код принят! Ожидайте.", reply_markup=user_main_kb)
            await state.clear()
            await show_my_tasks(message, user.id)
    else:
        await message.answer("Қате код. Қайтадан көріңіз. / Неверный код. Попробуйте снова.")

@router.message(F.text == "Менің тапсырмаларым / Мои задания")
async def cmd_my_tasks(message: types.Message):
    user = await rq.get_user_by_tg_id(message.from_user.id)
    if user:
        await show_my_tasks(message, user.id)
    else:
        await message.answer("Сіз тіркелмегенсіз. / Вы не зарегистрированы. /start")

async def show_my_tasks(message: types.Message, student_id: int):
    homeworks = await rq.get_active_homeworks(student_id)
    if not homeworks:
        await message.answer("Қазіргі уақытта үй тапсырмасы жоқ. / На данный момент заданий нет.")
        return

    buttons = []
    for hw in homeworks:
        deadline_str = hw.deadline.strftime("%d.%m")
        buttons.append([InlineKeyboardButton(
            text=f"🔘 {hw.description} (Дедлайн: {deadline_str})", 
            callback_data=f"student_hw_{hw.id}"
        )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Менің тапсырмаларым / Мои задания:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("student_hw_"))
async def process_homework_selection(callback: types.CallbackQuery, state: FSMContext):
    hw_id = int(callback.data.split("_")[2])
    hw = await rq.get_homework_by_id(hw_id)
    
    if not hw:
        await callback.message.answer("Тапсырма табылмады / Задание не найдено.")
        return

    deadline_str = hw.deadline.strftime("%d.%m %H:%M")
    caption = f"Тапсырма: {hw.description}\nДедлайн: {deadline_str}"
    if hw.text_content:
        caption += f"\n\n{hw.text_content}"
    
    await callback.message.answer(f"Сіз таңдадыңыз: {hw.description}\nШешімді жіберіңіз (фото/файл). / Вы выбрали: {hw.description}\nОтправьте решение (фото/файл).")
    
    if hw.file_id:
        try:
            await callback.message.answer_document(hw.file_id, caption=caption)
        except:
            await callback.message.answer_photo(hw.file_id, caption=caption)
    else:
        await callback.message.answer(caption)

    await state.update_data(homework_id=hw_id)
    await state.set_state(UserStates.waiting_for_submission)
    await callback.answer()

@router.message(UserStates.waiting_for_submission, F.content_type.in_({'document', 'photo'}))
async def process_submission(message: types.Message, state: FSMContext):
    data = await state.get_data()
    hw_id = data.get('homework_id')
    
    hw = await rq.get_homework_by_id(hw_id)
    if not hw:
        await message.answer("Ошибка. Задание не найдено.")
        await state.clear()
        return

    file_id = None
    if message.document:
        file_id = message.document.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id

    is_late = datetime.now() > hw.deadline
    await rq.submit_homework(hw.id, file_id, is_late)
    
    status_text = "Қабылданды ✅ (Вовремя)" if not is_late else "Қабылданды, бірақ дедлайннан кешіктірілді ⚠️"
    await message.answer(status_text)
    
  
    user = await rq.get_user_by_tg_id(message.from_user.id)
    admin_text = f"{user.name} сдал ДЗ '{hw.description}'!"
    if is_late:
        admin_text += " (С ОПОЗДАНИЕМ)"
    
    if settings.ADMIN_TELEGRAM_ID:
        await message.bot.send_message(settings.ADMIN_TELEGRAM_ID, admin_text)
        if message.document:
            await message.bot.send_document(settings.ADMIN_TELEGRAM_ID, file_id)
        elif message.photo:
            await message.bot.send_photo(settings.ADMIN_TELEGRAM_ID, file_id)
            
    await state.clear()
    await show_my_tasks(message, user.id)

@router.message(Command("claim"))
async def cmd_claim(message: types.Message):
    user = await rq.get_user_by_tg_id(message.from_user.id)
    if not user:
        await message.answer("Сіз тіркелмегенсіз. / Вы не зарегистрированы. /start")
        return
    await show_my_tasks(message, user.id)

@router.message(Command("upload"))
async def cmd_upload(message: types.Message):
    await message.answer("Тапсырманы таңдау үшін /start басыңыз. / Нажмите /start чтобы выбрать задание.")
