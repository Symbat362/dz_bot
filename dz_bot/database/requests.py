from sqlalchemy import select, update
from database.core import async_session
from database.models import User, Homework
from datetime import datetime
import random

async def add_student(name: str):
    async with async_session() as session:
        while True:
            code = str(random.randint(1000, 9999))
     
            existing = await session.scalar(select(User).where(User.access_code == code))
            if not existing:
                break
        
        user = User(name=name, access_code=code)
        session.add(user)
        await session.commit()
        return code

async def get_user_by_code(code: str):
    async with async_session() as session:
        return await session.scalar(select(User).where(User.access_code == code))

async def get_user_by_tg_id(tg_id: int):
    async with async_session() as session:
        return await session.scalar(select(User).where(User.telegram_id == tg_id))

async def attach_user_tg_id(code: str, tg_id: int):
    async with async_session() as session:
        await session.execute(update(User).where(User.access_code == code).values(telegram_id=tg_id))
        await session.commit()

async def get_all_students():
    async with async_session() as session:
        result = await session.execute(select(User))
        return result.scalars().all()

async def create_homework(student_id: int, deadline: datetime, description: str, file_id: str = None, text_content: str = None):
    async with async_session() as session:
        hw = Homework(
            student_id=student_id,
            deadline=deadline,
            description=description,
            file_id=file_id,
            text_content=text_content,
            status='assigned'
        )
        session.add(hw)
        await session.commit()
        return hw

async def get_active_homeworks(student_id: int):
    async with async_session() as session:
        stmt = select(Homework).where(
            Homework.student_id == student_id,
            Homework.status == 'assigned'
        ).order_by(Homework.deadline)
        result = await session.execute(stmt)
        return result.scalars().all()

async def get_homework_by_id(homework_id: int):
    async with async_session() as session:
        return await session.get(Homework, homework_id)

async def submit_homework(homework_id: int, solution_file_id: str, is_late: bool):
    async with async_session() as session:
        status = 'submitted_late' if is_late else 'submitted'
        await session.execute(
            update(Homework)
            .where(Homework.id == homework_id)
            .values(
                solution_file_id=solution_file_id,
                status=status,
                submitted_at=datetime.now()
            )
        )
        await session.commit()

async def get_student_homeworks(student_id: int):
    """
    Returns all homeworks for a student.
    """
    async with async_session() as session:
        stmt = select(Homework).where(Homework.student_id == student_id).order_by(Homework.id.desc())
        result = await session.execute(stmt)
        return result.scalars().all()

async def get_user_by_id(user_id: int):
    async with async_session() as session:
        return await session.get(User, user_id)

from sqlalchemy import delete

async def delete_student(student_id: int):
    async with async_session() as session:
        await session.execute(delete(Homework).where(Homework.student_id == student_id))
        await session.execute(delete(User).where(User.id == student_id))
        await session.commit()

async def delete_homework(homework_id: int):
    async with async_session() as session:
        await session.execute(delete(Homework).where(Homework.id == homework_id))
        await session.commit()
