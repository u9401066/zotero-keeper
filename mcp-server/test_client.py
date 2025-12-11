#!/usr/bin/env python3
"""
Test script for Zotero Client

測試與 Zotero Local API 的連線
"""

import asyncio
import sys
import json
from dataclasses import dataclass
from typing import Any, Optional

import httpx


# Inline the client classes to avoid import issues
class ZoteroConnectionError(Exception):
    pass

@dataclass
class ZoteroConfig:
    host: str = "YOUR_ZOTERO_HOST"
    port: int = 23119
    timeout: float = 30.0
    
    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def host_header(self) -> str:
        return f"127.0.0.1:{self.port}"


class ZoteroClient:
    def __init__(self, config: Optional[ZoteroConfig] = None):
        self.config = config or ZoteroConfig()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Host": self.config.host_header,
                },
            )
        return self._client
    
    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _request(self, method: str, path: str, json_data: Optional[dict] = None, params: Optional[dict] = None) -> Any:
        client = await self._get_client()
        response = await client.request(method=method, url=path, json=json_data, params=params)
        if response.text:
            try:
                return response.json()
            except:
                return response.text
        return None
    
    async def ping(self) -> bool:
        try:
            result = await self._request("GET", "/connector/ping")
            return "Zotero is running" in str(result)
        except:
            return False
    
    async def get_items(self, limit: int = 50) -> list:
        return await self._request("GET", "/api/users/0/items", params={"limit": limit})
    
    async def get_collections(self) -> list:
        return await self._request("GET", "/api/users/0/collections")
    
    async def get_tags(self) -> list:
        return await self._request("GET", "/api/users/0/tags")
    
    async def get_item_types(self) -> list:
        return await self._request("GET", "/api/itemTypes")


async def main():
    # 設定連線到 Windows 上的 Zotero
    config = ZoteroConfig(
        host="YOUR_ZOTERO_HOST",
        port=23119,
    )
    
    client = ZoteroClient(config)
    
    print("=" * 60)
    print("Zotero Client Test")
    print("=" * 60)
    print(f"Target: {config.base_url}")
    print(f"Host Header: {config.host_header}")
    print()
    
    try:
        # 1. Ping test
        print("1. Testing ping...")
        is_running = await client.ping()
        print(f"   Zotero running: {is_running}")
        
        if not is_running:
            print("   ❌ Cannot connect to Zotero")
            return
        
        print("   ✅ Connected to Zotero")
        print()
        
        # 2. Get items
        print("2. Getting items...")
        items = await client.get_items(limit=5)
        print(f"   Found {len(items)} items")
        for item in items[:3]:
            data = item.get("data", item)
            title = data.get("title", "No title")[:50]
            item_type = data.get("itemType", "unknown")
            print(f"   - [{item_type}] {title}")
        print()
        
        # 3. Get collections
        print("3. Getting collections...")
        collections = await client.get_collections()
        print(f"   Found {len(collections)} collections")
        for col in collections[:5]:
            data = col.get("data", col)
            name = data.get("name", "No name")
            print(f"   - {name}")
        print()
        
        # 4. Get tags
        print("4. Getting tags...")
        tags = await client.get_tags()
        print(f"   Found {len(tags)} tags")
        for tag in tags[:10]:
            tag_name = tag.get("tag", str(tag))
            print(f"   - {tag_name}")
        print()
        
        # 5. Get item types
        print("5. Getting item types...")
        types = await client.get_item_types()
        print(f"   Found {len(types)} item types")
        type_names = [t.get("itemType", str(t)) for t in types[:10]]
        print(f"   {', '.join(type_names)}...")
        print()
        
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
