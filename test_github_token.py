import os, httpx
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

async def test():
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://api.github.com/repos/SHRAVANIRANE/frontend-projects/contents",
            headers={"Authorization": f"token {GITHUB_TOKEN}"}
        )
        print(res.status_code, res.text)

import asyncio
asyncio.run(test())
