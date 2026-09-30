import asyncio
from sqlalchemy import select
from database.core import async_session, init_db
from database.models import User

students = [
    ("Санджар", "482931"),
    ("Бағым", "193847"),
    ("Аяулым", "920174"),
    ("Іңкәр", "481026"),
    ("Арсен", "374890"),
    ("Әбілмансұр", "209384"),
    ("Мұхаммед", "561203"),
    ("Алан", "490281"),
    ("Мейыржан", "738492"),
    ("Димаш", "820374"),
    ("Әлиайдар", "491203"),
    ("Айдай", "390485"),
    ("Айша", "572039"),
    ("Ділдә", "104928"),
    ("Әмина", "983210"),
]

async def seed():
    await init_db()
    async with async_session() as session:
        for name, code in students:
            # Check if user with this code already exists
            existing = await session.scalar(select(User).where(User.access_code == code))
            if not existing:
                user = User(name=name, access_code=code)
                session.add(user)
                print(f"Added {name} with code {code}")
            else:
                print(f"User with code {code} already exists ({existing.name})")
        
        await session.commit()

if __name__ == "__main__":
    asyncio.run(seed())
