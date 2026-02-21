# Browser Relay Client for OpenClaw

import httpx
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class BrowserRelayClient:
    """Client for OpenClaw browser relay"""
    
    def __init__(self, relay_url: str = "http://localhost:3000"):
        self.relay_url = relay_url
        self.session_id = None
    
    async def navigate(self, url: str) -> bool:
        """Navigate to URL"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.relay_url}/api/browser/navigate",
                json={"url": url},
                timeout=30.0
            )
            return response.status_code == 200
    
    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> bool:
        """Wait for element to appear"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.relay_url}/api/browser/wait",
                json={"selector": selector, "timeout": timeout},
                timeout=timeout / 1000 + 5
            )
            return response.status_code == 200
    
    async def query_selector_all(self, selector: str) -> List[Any]:
        """Get all elements matching selector"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.relay_url}/api/browser/query",
                json={"selector": selector},
                timeout=30.0
            )
            if response.status_code == 200:
                return response.json().get("elements", [])
            return []
    
    async def get_text(self, selector: str) -> str:
        """Get text content of element"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.relay_url}/api/browser/text",
                json={"selector": selector},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json().get("text", "")
            return ""
    
    async def scroll_down(self, amount: int = 1000) -> bool:
        """Scroll down the page"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.relay_url}/api/browser/scroll",
                json={"direction": "down", "amount": amount},
                timeout=10.0
            )
            return response.status_code == 200
