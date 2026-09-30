from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database import requests as rq
from states.admin import AdminStates
from config import settings
from datetime import datetime

router = Router()

router.message.filter(F.from_user.id == settings.ADMIN_TELEGRAM_ID)
router.callback_query.filter(F.from_user.id == settings.ADMIN_TELEGRAM_ID)

admin_main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Новое задание"), KeyboardButton(text="Список учеников")],
    [KeyboardButton(text="Добавить ученика")]
], resize_keyboard=True)

@router.message(CommandStart())
async def cmd_admin_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Админ-панель. Выберите действие:", reply_markup=admin_main_kb)

@router.message(F.text == "Добавить ученика")
@router.message(Command("add_student"))
async def cmd_add_student(message: types.Message, state: FSMContext):
    await message.answer("Введите имя нового ученика:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AdminStates.waiting_for_student_name)

@router.message(AdminStates.waiting_for_student_name)
async def process_add_student(message: types.Message, state: FSMContext):
    name = message.text.strip()
    code = await rq.add_student(name)
    await message.answer(f"Ученик {name} добавлен. Его код доступа: {code}", reply_markup=admin_main_kb)
    await state.clear()

@router.message(F.text == "Новое задание")
@router.message(Command("task"))
async def cmd_task(message: types.Message, state: FSMContext):
    await message.answer("Скиньте файл задания (PDF/Фото) или напишите текст.", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AdminStates.waiting_for_task_content)

@router.message(AdminStates.waiting_for_task_content, F.content_type.in_({'text', 'document', 'photo'}))
async def process_task_content(message: types.Message, state: FSMContext):
    if message.document:
        file_id = message.document.file_id
        text = message.caption
    elif message.photo:
        file_id = message.photo[-1].file_id
        text = message.caption
    else:
        file_id = None
        text = message.text

    await state.update_data(file_id=file_id, text=text)
    
    students = await rq.get_all_students()
    if not students:
        await message.answer("Нет зарегистрированных учеников. Используйте 'Добавить ученика'", reply_markup=admin_main_kb)
        await state.clear()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=student.name, callback_data=f"assign_{student.id}")] for student in students
    ])
    
    await message.answer("Выберите ученика / Оқушыны таңдаңыз:", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_for_student_selection)

@router.callback_query(AdminStates.waiting_for_student_selection, F.data.startswith("assign_"))
async def process_student_selection(callback: types.CallbackQuery, state: FSMContext):
    student_id = int(callback.data.split("_")[1])
    await state.update_data(student_id=student_id)
    await callback.message.answer("Напишите название задания (например: Геометрия 5 стр):")
    await state.set_state(AdminStates.waiting_for_task_description)
    await callback.answer()

@router.message(AdminStates.waiting_for_task_description)
async def process_task_description(message: types.Message, state: FSMContext):
    description = message.text.strip()
    await state.update_data(description=description)
    await message.answer("Введите дедлайн в формате: ДД.ММ ЧЧ:ММ (например: 05.12 23:00)")
    await state.set_state(AdminStates.waiting_for_deadline)

@router.message(AdminStates.waiting_for_deadline)
async def process_deadline(message: types.Message, state: FSMContext):
    try:
        date_str = message.text.strip()
        current_year = datetime.now().year
        full_date_str = f"{date_str} {current_year}"
        try:
            deadline = datetime.strptime(full_date_str, "%d.%m %H:%M %Y")
        except ValueError:
             deadline = datetime.strptime(full_date_str, "%d.%m %H.%M %Y")

        data = await state.get_data()
        student_id = data['student_id']
        file_id = data.get('file_id')
        text = data.get('text')
        description = data.get('description')
        
        await rq.create_homework(student_id, deadline, description, file_id, text)
        
        student = await rq.get_user_by_id(student_id)
        await message.answer(f"Задание '{description}' назначено {student.name}. Дедлайн: {deadline}", reply_markup=admin_main_kb)
        
        if student.telegram_id:
            try:
                notification = f"Вам назначено новое задание: {description}!\nДедлайн: {deadline}"
                if text:
                    notification += f"\n\n{text}"
                
                if file_id:
                    try:
                        await message.bot.send_document(student.telegram_id, file_id, caption=notification)
                    except:
                        await message.bot.send_photo(student.telegram_id, file_id, caption=notification)
                else:
                    await message.bot.send_message(student.telegram_id, notification)
            except Exception as e:
                await message.answer(f"Не удалось отправить уведомление ученику: {e}")
        
        await state.clear()
        
    except ValueError:
        await message.answer("Неверный формат даты. Попробуйте еще раз: ДД.ММ ЧЧ:ММ (например: 05.12 23:00)")

@router.message(F.text == "Список учеников")
@router.message(Command("check"))
async def cmd_check(message: types.Message):
    students = await rq.get_all_students()
    if not students:
        await message.answer("Нет учеников.")
        return

    buttons = []
    for student in students:
        buttons.append([InlineKeyboardButton(text=student.name, callback_data=f"manage_student_{student.id}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите ученика:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("manage_student_"))
async def process_manage_student(callback: types.CallbackQuery):
    student_id = int(callback.data.split("_")[2])
    student = await rq.get_user_by_id(student_id)
    
    if not student:
        await callback.message.answer("Ученик не найден.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Проверить ДЗ", callback_data=f"check_student_{student.id}")],
        [InlineKeyboardButton(text="Удалить ученика", callback_data=f"delete_student_{student.id}")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_students")]
    ])
    
    await callback.message.edit_text(f"Ученик: {student.name}\nКод: {student.access_code}", reply_markup=keyboard)

@router.callback_query(F.data == "back_to_students")
async def back_to_students(callback: types.CallbackQuery):
    await callback.message.delete()
    await cmd_check(callback.message)

@router.callback_query(F.data.startswith("delete_student_"))
async def process_delete_student(callback: types.CallbackQuery):
    student_id = int(callback.data.split("_")[2])
    await rq.delete_student(student_id)
    await callback.answer("Ученик удален.")
    await back_to_students(callback)

@router.callback_query(F.data.startswith("check_student_"))
async def process_check_student_selection(callback: types.CallbackQuery):
    student_id = int(callback.data.split("_")[2])
    homeworks = await rq.get_student_homeworks(student_id)
    
    if not homeworks:
        await callback.message.answer("У этого ученика нет заданий.")
        await callback.answer()
        return

    buttons = []
    for hw in homeworks:
        status_icon = "⚪️"
        if hw.status == 'assigned':
            status_icon = "🔴" # Not submitted
        elif hw.status == 'submitted':
            status_icon = "🟢" # Submitted on time
        elif hw.status == 'submitted_late':
            status_icon = "🟡" # Submitted late
        
        buttons.append([InlineKeyboardButton(
            text=f"{status_icon} {hw.description}", 
            callback_data=f"view_hw_{hw.id}"
        )])
    
    buttons.append([InlineKeyboardButton(text="Назад", callback_data=f"manage_student_{student_id}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Задания ученика:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("view_hw_"))
async def process_view_homework(callback: types.CallbackQuery):
    hw_id = int(callback.data.split("_")[2])
    hw = await rq.get_homework_by_id(hw_id)
    
    if not hw:
        await callback.message.answer("Задание не найдено.")
        return

    info = f"Задание: {hw.description}\nСтатус: {hw.status}\nДедлайн: {hw.deadline}"
    if hw.submitted_at:
        info += f"\nСдано: {hw.submitted_at}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить задание", callback_data=f"delete_hw_{hw.id}")],
        [InlineKeyboardButton(text="Назад", callback_data=f"check_student_{hw.student_id}")]
    ])
    
    await callback.message.answer(info, reply_markup=keyboard)
    
    if hw.solution_file_id:
        try:
            await callback.message.answer_document(hw.solution_file_id)
        except:
            await callback.message.answer_photo(hw.solution_file_id)
    elif hw.status == 'assigned':
        await callback.message.answer("Решение еще не отправлено.")
            
    await callback.answer()

@router.callback_query(F.data.startswith("delete_hw_"))
async def process_delete_homework(callback: types.CallbackQuery):
    hw_id = int(callback.data.split("_")[2])
    hw = await rq.get_homework_by_id(hw_id)
    if hw:
        student_id = hw.student_id
        await rq.delete_homework(hw_id)
        await callback.answer("Задание удалено.")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад к списку", callback_data=f"check_student_{student_id}")]
        ])
        await callback.message.edit_text("Задание удалено.", reply_markup=keyboard)
    else:
        await callback.answer("Задание уже удалено.")
