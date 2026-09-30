from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from datetime import datetime

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String)
    access_code: Mapped[str] = mapped_column(String, unique=True)

class Homework(Base):
    __tablename__ = 'homeworks'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    

    file_id: Mapped[str] = mapped_column(String, nullable=True)
    text_content: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    
    deadline: Mapped[datetime] = mapped_column(DateTime)
    
    # Student submission
    solution_file_id: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default='assigned') # assigned, submitted, submitted_late
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    student: Mapped["User"] = relationship()
