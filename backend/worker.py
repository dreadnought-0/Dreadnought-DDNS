#!/usr/bin/env python3
import os
import asyncio
import logging
import signal
import sys
import traceback
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import create_tables
from sync_service import SyncService
from models import Setting
from database import SessionLocal
from discord_notifier import DiscordNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DDNSWorker:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.sync_service = None
        self.running = False
        self.discord = DiscordNotifier()

        # Get poll interval from environment or database
        self.poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
        
    def _get_setting(self, key: str, default: str = "") -> str:
        """Get setting from database"""
        try:
            with SessionLocal() as db:
                setting = db.query(Setting).filter(Setting.key == key).first()
                return setting.value if setting else default
        except Exception as e:
            logger.warning(f"Failed to get setting {key}: {e}")
            return default
    
    def _set_setting(self, key: str, value: str):
        """Set setting in database"""
        try:
            with SessionLocal() as db:
                setting = db.query(Setting).filter(Setting.key == key).first()
                if setting:
                    setting.value = value
                else:
                    setting = Setting(key=key, value=value)
                    db.add(setting)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
    
    async def sync_task(self):
        """Periodic sync task"""
        try:
            logger.info("Starting periodic sync...")
            result = await self.sync_service.sync_all_records()

            if result["status"] == "completed":
                if result["records_processed"] == 0:
                    logger.info("No records to sync (no IP changes)")
                else:
                    logger.info(
                        f"Sync completed: {result['records_updated']} updated, "
                        f"{result['records_failed']} failed, "
                        f"duration: {result['duration_seconds']:.2f}s"
                    )
            else:
                logger.error(f"Sync failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Sync task failed: {e}")
            # Send unexpected error notification
            tb_str = traceback.format_exc()
            await self.discord.notify_unexpected_error(
                error_type=type(e).__name__,
                error_message=f"Worker sync task failed: {str(e)}",
                traceback=tb_str
            )
    
    async def initialize(self):
        """Initialize the worker"""
        logger.info("Initializing DDNS Worker...")
        
        # Create database tables first
        create_tables()
        
        # Initialize sync service after database is ready
        self.sync_service = SyncService()
        
        # Update poll interval from database if available
        db_poll_interval = self._get_setting("poll_interval_seconds")
        if db_poll_interval:
            try:
                self.poll_interval = int(db_poll_interval)
            except ValueError:
                logger.warning(f"Invalid poll interval in database: {db_poll_interval}")
        
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        
        # Set up scheduler
        self.scheduler.add_job(
            self.sync_task,
            trigger=IntervalTrigger(seconds=self.poll_interval),
            id="periodic_sync",
            name="Periodic DDNS Sync",
            max_instances=1,
            coalesce=True
        )
        
        # Initial sync
        await self.sync_task()
        
        logger.info("Worker initialized successfully")
    
    async def start(self):
        """Start the worker"""
        self.running = True
        self.scheduler.start()
        logger.info("DDNS Worker started")
        
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the worker"""
        if self.running:
            logger.info("Stopping DDNS Worker...")
            self.running = False
            self.scheduler.shutdown(wait=True)
            logger.info("DDNS Worker stopped")
    
    def handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        self.running = False


async def main():
    worker = DDNSWorker()

    # Set up signal handlers
    signal.signal(signal.SIGTERM, worker.handle_signal)
    signal.signal(signal.SIGINT, worker.handle_signal)

    try:
        await worker.initialize()
        await worker.start()
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        # Send unexpected error notification
        tb_str = traceback.format_exc()
        await worker.discord.notify_unexpected_error(
            error_type=type(e).__name__,
            error_message=f"Worker initialization/startup failed: {str(e)}",
            traceback=tb_str
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())