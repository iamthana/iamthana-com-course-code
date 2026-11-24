import os
from datetime import date

import httpx2

from auth import require_scope


async def fetch_sales(day: str, http: httpx2.AsyncClient) -> str:
    """Calls the POS API with this server's own credential, never with the caller's token."""
    require_scope("orders:read")
    day = date.fromisoformat(day).isoformat()
    response = await http.get(
        f"https://pos.example.com/sales/{day}",
        headers={"Authorization": f"Bearer {os.environ['POS_API_TOKEN']}"},
    )
    response.raise_for_status()
    return response.text
