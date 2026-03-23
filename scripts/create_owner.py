#!/usr/bin/env python3
"""
One-time script to bootstrap the first owner user.
Run: python scripts/create_owner.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import AsyncSessionLocal
from app.db.models import User
from app.auth.service import hash_password
from sqlalchemy import select


async def main():
    email = input("Owner email: ").strip()
    password = input("Password: ").strip()

    if not email or not password:
        print("Email and password are required.")
        sys.exit(1)

    if len(password) < 12:
        print("Password must be at least 12 characters.")
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print(f"User {email} already exists.")
            sys.exit(1)

        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            role="owner",
        )
        db.add(user)
        await db.commit()
        print(f"\n✓ Owner created: {email}")
        print(f"  ID: {user.id}")


if __name__ == "__main__":
    asyncio.run(main())