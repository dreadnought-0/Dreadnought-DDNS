import os
import asyncio
from typing import Optional, List
import httpx
import logging

logger = logging.getLogger(__name__)


class IPDetectionError(Exception):
    pass


class IPDetector:
    def __init__(self, ipv6_enabled: bool = True):
        self.ipv6_enabled = ipv6_enabled
        self.timeout = httpx.Timeout(10.0)
        
        # IPv4 endpoints in priority order
        self.ipv4_endpoints = [
            "https://api.ipify.org",
            "https://icanhazip.com",
            "https://ifconfig.me/ip",
            "https://ipecho.net/plain"
        ]
        
        # IPv6 endpoints in priority order
        self.ipv6_endpoints = [
            "https://api6.ipify.org",
            "https://ifconfig.co/ip",
            "https://v6.ident.me"
        ] if ipv6_enabled else []
    
    async def _fetch_ip_from_endpoint(self, url: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if ip and self._is_valid_ip(ip):
                        return ip
        except Exception as e:
            logger.debug(f"Failed to get IP from {url}: {e}")
        return None
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Basic IP validation"""
        import re
        
        # IPv4 pattern
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        # IPv6 pattern (simplified)
        ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
        
        if re.match(ipv4_pattern, ip):
            # Validate IPv4 octets
            octets = ip.split('.')
            return all(0 <= int(octet) <= 255 for octet in octets)
        elif re.match(ipv6_pattern, ip):
            return True
        
        return False
    
    async def get_ipv4(self) -> Optional[str]:
        """Get current IPv4 address"""
        for endpoint in self.ipv4_endpoints:
            ip = await self._fetch_ip_from_endpoint(endpoint)
            if ip:
                logger.debug(f"Got IPv4 {ip} from {endpoint}")
                return ip
        
        logger.warning("Failed to detect IPv4 from all endpoints")
        return None
    
    async def get_ipv6(self) -> Optional[str]:
        """Get current IPv6 address"""
        if not self.ipv6_enabled:
            return None
        
        for endpoint in self.ipv6_endpoints:
            ip = await self._fetch_ip_from_endpoint(endpoint)
            if ip:
                logger.debug(f"Got IPv6 {ip} from {endpoint}")
                return ip
        
        logger.warning("Failed to detect IPv6 from all endpoints")
        return None
    
    async def get_current_ips(self) -> tuple[Optional[str], Optional[str]]:
        """Get both IPv4 and IPv6 concurrently. Returns (ipv4, ipv6)"""
        tasks = []
        
        # Always try to get IPv4
        tasks.append(self.get_ipv4())
        
        # Get IPv6 if enabled
        if self.ipv6_enabled:
            tasks.append(self.get_ipv6())
        else:
            # Create a simple coroutine that returns None
            async def return_none():
                return None
            tasks.append(return_none())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        ipv4 = results[0] if not isinstance(results[0], Exception) else None
        ipv6 = results[1] if not isinstance(results[1], Exception) else None
        
        return ipv4, ipv6