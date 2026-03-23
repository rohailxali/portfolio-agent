import asyncio
import sys
sys.path.insert(0, '.')

from app.db.session import AsyncSessionLocal
from app.db.models import User
from app.auth.service import hash_password


async def main():
    email = input('Email: ')
    password = input('Password: ')
    
    async with AsyncSessionLocal() as db:
        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            role='owner',
        )
        db.add(user)
        await db.commit()
        print(f'✓ Owner created: {email}')


asyncio.run(main())