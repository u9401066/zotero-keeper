import asyncio
import httpx


async def test():
    async with httpx.AsyncClient() as client:
        # Test connector ping
        r = await client.get("http://localhost:23119/connector/ping")
        print(f"Connector Ping: {r.status_code}")

        # Test Local API
        r = await client.get("http://localhost:23119/api/users/0/items?limit=3")
        items = r.json()
        print(f"Local API: {len(items)} items returned")
        if items:
            title = items[0].get("data", {}).get("title", "No title")
            print(f"First item: {title[:50]}...")


if __name__ == "__main__":
    asyncio.run(test())
