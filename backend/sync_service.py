import os
import asyncio
import logging
import traceback
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import SessionLocal
from models import TrackedRecord, Setting, AuditLog
from cf_client import CloudflareClient, CloudflareError
from ip_detection import IPDetector
from discord_notifier import DiscordNotifier

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self):
        self.cf_client = CloudflareClient()
        self.ip_detector = IPDetector(ipv6_enabled=self._get_setting("ipv6_enabled", "true") == "true")
        self.discord = DiscordNotifier()
    
    def _get_setting(self, key: str, default: str = "") -> str:
        """Get setting from database"""
        try:
            with SessionLocal() as db:
                setting = db.query(Setting).filter(Setting.key == key).first()
                return setting.value if setting else default
        except Exception as e:
            logger.warning(f"Failed to get setting {key} from database: {e}")
            return default
    
    def _set_setting(self, key: str, value: str):
        """Set setting in database"""
        with SessionLocal() as db:
            setting = db.query(Setting).filter(Setting.key == key).first()
            if setting:
                setting.value = value
            else:
                setting = Setting(key=key, value=value)
                db.add(setting)
            db.commit()
    
    def _log_audit(self, action: str, details: Dict[str, Any]):
        """Add audit log entry"""
        with SessionLocal() as db:
            audit = AuditLog(action=action, details=details)
            db.add(audit)
            db.commit()
    
    async def _resolve_zone_id(self, db: Session, record: TrackedRecord) -> Optional[str]:
        """Resolve and cache zone_id for a domain"""
        if record.zone_id_cached:
            return record.zone_id_cached
        
        try:
            zone_id = await self.cf_client.get_zone_id(record.domain)
            if zone_id:
                record.zone_id_cached = zone_id
                db.commit()
                return zone_id
        except CloudflareError as e:
            logger.error(f"Failed to resolve zone_id for {record.domain}: {e}")
        
        return None
    
    async def _check_cname_conflict(self, zone_id: str, fqdn: str) -> bool:
        """Check if there's a CNAME record that would conflict with A/AAAA"""
        try:
            existing_records = await self.cf_client.list_dns_records(zone_id, "CNAME", fqdn)
            return len(existing_records) > 0
        except CloudflareError:
            return False
    
    async def sync_record(self, db: Session, record: TrackedRecord, ip: str) -> Dict[str, Any]:
        """Sync a single record with Cloudflare"""
        result = {
            "record_id": record.id,
            "fqdn": record.fqdn,
            "type": record.type,
            "status": "error",
            "message": "",
            "action": None
        }
        
        try:
            # Resolve zone_id
            zone_id = await self._resolve_zone_id(db, record)
            if not zone_id:
                result["message"] = f"Could not resolve zone_id for domain {record.domain}"
                return result
            
            # Check for CNAME conflicts
            if await self._check_cname_conflict(zone_id, record.fqdn):
                result["message"] = f"CNAME record exists for {record.fqdn}, cannot create A/AAAA record"
                return result
            
            # Check if record already exists with same content
            existing_records = await self.cf_client.list_dns_records(zone_id, record.type, record.fqdn)
            existing_content = existing_records[0].get("content") if existing_records else None
            ip_changed = existing_content != ip

            # Upsert DNS record
            cf_record, action = await self.cf_client.upsert_dns_record(
                zone_id=zone_id,
                record_type=record.type,
                name=record.fqdn,
                content=ip,
                proxied=record.proxied,
                ttl=record.ttl
            )

            result.update({
                "status": "success",
                "action": action,
                "message": f"Successfully {action} {record.type} record for {record.fqdn} -> {ip}",
                "cloudflare_id": cf_record.get("id"),
                "ip": ip
            })

            # Send success notification only if IP actually changed
            if ip_changed:
                await self.discord.notify_dns_update_success(record.fqdn, record.type, ip)

        except CloudflareError as e:
            result["message"] = f"Cloudflare error: {e}"
            logger.error(f"Failed to sync record {record.fqdn}: {e}")

            # Send failure notification
            await self.discord.notify_dns_update_failure(record.fqdn, record.type, str(e))

        except Exception as e:
            result["message"] = f"Unexpected error: {e}"
            logger.error(f"Unexpected error syncing record {record.fqdn}: {e}")

            # Send failure notification with traceback
            tb_str = traceback.format_exc()
            await self.discord.notify_dns_update_failure(record.fqdn, record.type, f"{str(e)}\n\nTraceback:\n{tb_str[:500]}")
        
        return result
    
    async def sync_all_records(self) -> Dict[str, Any]:
        """Sync all tracked records based on current IP"""
        start_time = datetime.now()
        results = {
            "start_time": start_time.isoformat(),
            "status": "running",
            "ipv4": None,
            "ipv6": None,
            "records_processed": 0,
            "records_updated": 0,
            "records_failed": 0,
            "details": []
        }
        
        try:
            # Get current IPs
            current_ipv4, current_ipv6 = await self.ip_detector.get_current_ips()
            results["ipv4"] = current_ipv4
            results["ipv6"] = current_ipv6
            
            # Get last seen IPs
            last_ipv4 = self._get_setting("last_seen_ipv4")
            last_ipv6 = self._get_setting("last_seen_ipv6")

            # Only consider it a "change" if we had a previous IP and it's different
            # Don't notify on first run when last_ipv4/ipv6 are empty
            ip_changed = (
                (current_ipv4 and last_ipv4 and current_ipv4 != last_ipv4) or
                (current_ipv6 and last_ipv6 and current_ipv6 != last_ipv6)
            )

            # Send IP change notification only if IPs actually changed (not first run)
            if ip_changed:
                await self.discord.notify_ip_change(last_ipv4, current_ipv4, last_ipv6, current_ipv6)
            
            with SessionLocal() as db:
                records_to_sync = []
                
                # Get records that need syncing based on IP changes
                if current_ipv4 and current_ipv4 != last_ipv4:
                    ipv4_records = db.query(TrackedRecord).filter(TrackedRecord.type == "A").all()
                    records_to_sync.extend([(record, current_ipv4) for record in ipv4_records])
                
                if current_ipv6 and current_ipv6 != last_ipv6:
                    ipv6_records = db.query(TrackedRecord).filter(TrackedRecord.type == "AAAA").all()
                    records_to_sync.extend([(record, current_ipv6) for record in ipv6_records])
                
                results["records_processed"] = len(records_to_sync)
                
                # Sync records
                for record, ip in records_to_sync:
                    sync_result = await self.sync_record(db, record, ip)
                    results["details"].append(sync_result)
                    
                    if sync_result["status"] == "success":
                        results["records_updated"] += 1
                    else:
                        results["records_failed"] += 1
                
                # Update last seen IPs if changed
                if current_ipv4 and current_ipv4 != last_ipv4:
                    self._set_setting("last_seen_ipv4", current_ipv4)
                if current_ipv6 and current_ipv6 != last_ipv6:
                    self._set_setting("last_seen_ipv6", current_ipv6)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            results.update({
                "status": "completed",
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "ip_changed": ip_changed
            })
            
            # Update sync status
            self._set_setting("last_sync_at", end_time.isoformat())
            self._set_setting("last_sync_result", f"Processed {results['records_processed']} records, {results['records_updated']} updated, {results['records_failed']} failed")
            
            # Log audit entry
            self._log_audit("bulk_sync", {
                "records_processed": results["records_processed"],
                "records_updated": results["records_updated"],
                "records_failed": results["records_failed"],
                "duration_seconds": duration,
                "ip_changed": ip_changed,
                "current_ipv4": current_ipv4,
                "current_ipv6": current_ipv6
            })
            
        except Exception as e:
            results.update({
                "status": "error",
                "error": str(e),
                "end_time": datetime.now().isoformat()
            })
            logger.error(f"Sync failed with error: {e}")

            # Send sync error notification
            tb_str = traceback.format_exc()
            await self.discord.notify_sync_error(
                error_message=str(e),
                details=tb_str[:1000]
            )
        
        return results
    
    async def sync_single_record_immediate(self, record: TrackedRecord) -> Dict[str, Any]:
        """Immediately sync a single record using current IP"""
        current_ipv4, current_ipv6 = await self.ip_detector.get_current_ips()
        
        # Determine which IP to use based on record type
        if record.type == "A" and current_ipv4:
            ip = current_ipv4
        elif record.type == "AAAA" and current_ipv6:
            ip = current_ipv6
        else:
            return {
                "record_id": record.id,
                "fqdn": record.fqdn,
                "type": record.type,
                "status": "error",
                "message": f"No suitable IP found for {record.type} record"
            }
        
        with SessionLocal() as db:
            result = await self.sync_record(db, record, ip)
            
            # Log audit entry
            self._log_audit("immediate_sync", {
                "record_id": record.id,
                "fqdn": record.fqdn,
                "type": record.type,
                "result": result
            })
            
            return result