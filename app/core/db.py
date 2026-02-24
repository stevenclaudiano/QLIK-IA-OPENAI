import asyncpg
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:12345678@localhost:5432/UsersBi"
)

async def get_connection():
    return await asyncpg.connect(DATABASE_URL)
