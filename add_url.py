import asyncio
from amboss.db import DatabaseManager

async def add_url():
    async with DatabaseManager() as db:
        await db.add_url('--0D-i', 'https://next.amboss.com/de/article/--0D-i')
        print("✅ Added URL to database")

if __name__ == "__main__":
    asyncio.run(add_url()) 