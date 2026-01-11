import os
import logging
from typing import Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Service for sending Discord webhook notifications"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")

    async def send_notification(self, title: str, description: str, color: int = 0x5865F2, fields: list = None):
        """
        Send a Discord webhook notification

        Args:
            title: Notification title
            description: Notification description
            color: Embed color (default: Discord Blurple)
            fields: List of embed fields [{"name": "...", "value": "...", "inline": bool}]
        """
        if not self.webhook_url:
            logger.debug("Discord webhook URL not configured, skipping notification")
            return

        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "DarkDDNS"
            }
        }

        if fields:
            embed["fields"] = fields

        payload = {
            "embeds": [embed]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(f"Discord notification sent: {title}")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")

    async def notify_dns_update_success(self, record_name: str, record_type: str, ip_address: str):
        """Notify when a DNS record is successfully updated"""
        await self.send_notification(
            title="✅ DNS Record Updated",
            description=f"Successfully updated DNS record",
            color=0x57F287,  # Green
            fields=[
                {"name": "Record", "value": record_name, "inline": True},
                {"name": "Type", "value": record_type, "inline": True},
                {"name": "IP Address", "value": ip_address, "inline": False}
            ]
        )

    async def notify_dns_update_failure(self, record_name: str, record_type: str, error: str):
        """Notify when a DNS record update fails"""
        await self.send_notification(
            title="❌ DNS Update Failed",
            description=f"Failed to update DNS record",
            color=0xED4245,  # Red
            fields=[
                {"name": "Record", "value": record_name, "inline": True},
                {"name": "Type", "value": record_type, "inline": True},
                {"name": "Error", "value": error[:1024], "inline": False}
            ]
        )

    async def notify_ip_change(self, old_ipv4: Optional[str], new_ipv4: Optional[str],
                               old_ipv6: Optional[str], new_ipv6: Optional[str]):
        """Notify when IP address changes are detected"""
        fields = []

        # Normalize empty strings to None for proper comparison
        old_ipv4 = old_ipv4 or None
        new_ipv4 = new_ipv4 or None
        old_ipv6 = old_ipv6 or None
        new_ipv6 = new_ipv6 or None

        # Only notify if there's an actual change (both values must exist and be different)
        if old_ipv4 and new_ipv4 and old_ipv4 != new_ipv4:
            fields.append({
                "name": "IPv4 Changed",
                "value": f"**Old:** {old_ipv4}\n**New:** {new_ipv4}",
                "inline": False
            })

        if old_ipv6 and new_ipv6 and old_ipv6 != new_ipv6:
            fields.append({
                "name": "IPv6 Changed",
                "value": f"**Old:** {old_ipv6}\n**New:** {new_ipv6}",
                "inline": False
            })

        if fields:
            await self.send_notification(
                title="🔄 IP Address Changed",
                description="Your public IP address has changed",
                color=0xFEE75C,  # Yellow
                fields=fields
            )

    async def notify_sync_error(self, error_message: str, details: Optional[str] = None):
        """Notify when a sync error occurs"""
        fields = [
            {"name": "Error", "value": error_message[:1024], "inline": False}
        ]

        if details:
            fields.append({
                "name": "Details",
                "value": details[:1024],
                "inline": False
            })

        await self.send_notification(
            title="⚠️ Sync Error",
            description="An error occurred during DNS synchronization",
            color=0xFEE75C,  # Yellow
            fields=fields
        )

    async def notify_unexpected_error(self, error_type: str, error_message: str, traceback: Optional[str] = None):
        """Notify when an unexpected error occurs"""
        fields = [
            {"name": "Error Type", "value": error_type, "inline": True},
            {"name": "Message", "value": error_message[:1024], "inline": False}
        ]

        if traceback:
            # Truncate traceback if too long
            tb_preview = traceback[:500] + "..." if len(traceback) > 500 else traceback
            fields.append({
                "name": "Traceback",
                "value": f"```\n{tb_preview}\n```",
                "inline": False
            })

        await self.send_notification(
            title="🚨 Unexpected Error",
            description="An unexpected error occurred in the DDNS service",
            color=0xED4245,  # Red
            fields=fields
        )
