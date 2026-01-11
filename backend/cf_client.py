import os
import asyncio
import random
from typing import Optional, List, Dict, Any
import httpx
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CloudflareError(Exception):
    def __init__(self, message: str, status_code: int = None, errors: List[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors or []


class CloudflareClient:
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("CF_API_TOKEN")
        if not self.api_token:
            raise ValueError("Cloudflare API token is required")
        
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        self.timeout = httpx.Timeout(15.0)
        self.rate_limit_delay = 0
        self.last_request_time = datetime.now()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Dict[Any, Any]:
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(max_retries + 1):
            try:
                # Apply rate limiting delay
                if self.rate_limit_delay > 0:
                    await asyncio.sleep(self.rate_limit_delay)
                    self.rate_limit_delay = 0
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        params=params,
                        json=json_data
                    )
                
                self.last_request_time = datetime.now()
                
                if response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < max_retries:
                        delay = min(retry_after + random.uniform(0, 5), 300)  # Max 5 min
                        logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise CloudflareError(
                            "Rate limit exceeded, max retries reached",
                            status_code=429
                        )
                
                data = response.json()
                
                if not data.get("success", False):
                    errors = data.get("errors", [])
                    error_msg = "; ".join([err.get("message", "Unknown error") for err in errors])
                    
                    # Redact token from error messages
                    if self.api_token in error_msg:
                        error_msg = error_msg.replace(self.api_token, "[REDACTED]")
                    
                    raise CloudflareError(
                        f"Cloudflare API error: {error_msg}",
                        status_code=response.status_code,
                        errors=errors
                    )
                
                return data
                
            except httpx.TimeoutException:
                if attempt < max_retries:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Request timeout, retrying in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise CloudflareError("Request timeout after all retries")
            
            except httpx.RequestError as e:
                if attempt < max_retries:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Request error: {e}, retrying in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise CloudflareError(f"Request failed after all retries: {e}")
        
        raise CloudflareError("Unexpected error in request handling")
    
    async def list_zones(self, name: Optional[str] = None) -> List[Dict]:
        params = {}
        if name:
            params["name"] = name
        
        data = await self._make_request("GET", "/zones", params=params)
        return data.get("result", [])
    
    async def get_zone_id(self, domain: str) -> Optional[str]:
        zones = await self.list_zones(name=domain)
        if zones:
            return zones[0]["id"]
        return None
    
    async def list_dns_records(
        self,
        zone_id: str,
        record_type: Optional[str] = None,
        name: Optional[str] = None
    ) -> List[Dict]:
        params = {}
        if record_type:
            params["type"] = record_type
        if name:
            params["name"] = name
        
        data = await self._make_request("GET", f"/zones/{zone_id}/dns_records", params=params)
        return data.get("result", [])
    
    async def create_dns_record(
        self,
        zone_id: str,
        record_type: str,
        name: str,
        content: str,
        proxied: bool = False,
        ttl: int = 300
    ) -> Dict:
        # For proxied records, Cloudflare ignores custom TTL
        if proxied:
            ttl = 1  # Auto
        
        json_data = {
            "type": record_type,
            "name": name,
            "content": content,
            "proxied": proxied,
            "ttl": ttl
        }
        
        data = await self._make_request("POST", f"/zones/{zone_id}/dns_records", json_data=json_data)
        return data.get("result", {})
    
    async def update_dns_record(
        self,
        zone_id: str,
        record_id: str,
        record_type: str,
        name: str,
        content: str,
        proxied: bool = False,
        ttl: int = 300
    ) -> Dict:
        # For proxied records, Cloudflare ignores custom TTL
        if proxied:
            ttl = 1  # Auto
        
        json_data = {
            "type": record_type,
            "name": name,
            "content": content,
            "proxied": proxied,
            "ttl": ttl
        }
        
        data = await self._make_request("PUT", f"/zones/{zone_id}/dns_records/{record_id}", json_data=json_data)
        return data.get("result", {})
    
    async def delete_dns_record(self, zone_id: str, record_id: str) -> bool:
        data = await self._make_request("DELETE", f"/zones/{zone_id}/dns_records/{record_id}")
        return data.get("result", {}).get("id") == record_id
    
    async def upsert_dns_record(
        self,
        zone_id: str,
        record_type: str,
        name: str,
        content: str,
        proxied: bool = False,
        ttl: int = 300
    ) -> tuple[Dict, str]:
        """
        Creates or updates a DNS record. Returns (record_data, action)
        where action is either 'created' or 'updated'
        """
        # Check if record exists
        existing_records = await self.list_dns_records(zone_id, record_type, name)
        
        if existing_records:
            # Update existing record
            record = existing_records[0]
            updated_record = await self.update_dns_record(
                zone_id, record["id"], record_type, name, content, proxied, ttl
            )
            return updated_record, "updated"
        else:
            # Create new record
            new_record = await self.create_dns_record(
                zone_id, record_type, name, content, proxied, ttl
            )
            return new_record, "created"