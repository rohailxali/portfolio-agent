import asyncio
import sys
sys.path.insert(0, '.')

from app.db.session import AsyncSessionLocal
from app.db.models import User
from app.auth.service import hash_password
from sqlalchemy import delete


async def main():
    email = input('Email: ')
    password = input('New password: ')

    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email == email))
        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            role='owner',
        )
        db.add(user)
        await db.commit()
        print('✓ Password reset successfully')


asyncio.run(main())