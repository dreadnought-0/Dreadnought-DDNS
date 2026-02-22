import os
import logging
import traceback
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Response, Cookie, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from database import get_db, create_tables
from models import User, TrackedRecord, Setting, AuditLog, Domain
from schemas import (
    UserCreate, UserLogin, TrackedRecordCreate, TrackedRecordUpdate,
    TrackedRecord as TrackedRecordSchema, SyncStatus, AuditEntry,
    ImportRequest, ImportRecord, SettingUpdate,
    DomainCreate, DomainUpdate, Domain as DomainSchema
)
from auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from sync_service import SyncService
from ip_detection import IPDetector
from discord_notifier import DiscordNotifier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DDNS Manager API",
    description="Self-hosted DDNS Manager for Cloudflare",
    version="1.0.0"
)

# CORS middleware
# Use CORS_ORIGINS env var (comma-separated) for production; defaults to wildcard for local use.
# Note: allow_credentials=True with allow_origins=["*"] causes browsers to reflect the Origin
# header rather than returning "*", meaning any origin gets credentialed access. Set
# CORS_ORIGINS explicitly in production (e.g. "https://ddns.example.com").
_cors_env = os.getenv("CORS_ORIGINS", "")
cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler for unexpected errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions and send Discord notifications"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Send Discord notification for unexpected errors
    discord = DiscordNotifier()
    tb_str = traceback.format_exc()
    await discord.notify_unexpected_error(
        error_type=type(exc).__name__,
        error_message=str(exc),
        traceback=tb_str
    )

    # Return a generic message; never expose exception details to clients
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected internal error occurred."}
    )


# Initialize database first
create_tables()

# Services are initialised inside startup_event so that a missing CF_API_TOKEN
# does not crash the process at import time.
sync_service: Optional[SyncService] = None
ip_detector: Optional[IPDetector] = None

# Whether to set the Secure flag on the session cookie.
# Enable this whenever the app is served over HTTPS.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("1", "true", "yes")

_DEFAULT_ADMIN_EMAIL = "admin@localhost.local"
_DEFAULT_ADMIN_PASSWORD = "ChangeMe!"


async def create_admin_user():
    """Create default admin user if it doesn't exist"""
    admin_email = os.getenv("ADMIN_EMAIL", _DEFAULT_ADMIN_EMAIL)
    admin_password = os.getenv("ADMIN_PASSWORD", _DEFAULT_ADMIN_PASSWORD)

    if admin_email == _DEFAULT_ADMIN_EMAIL or admin_password == _DEFAULT_ADMIN_PASSWORD:
        logger.warning(
            "ADMIN_EMAIL or ADMIN_PASSWORD is using the insecure default value. "
            "Set ADMIN_EMAIL and ADMIN_PASSWORD environment variables before deploying."
        )

    with next(get_db()) as db:
        existing_user = db.query(User).filter(User.email == admin_email).first()
        if not existing_user:
            hashed_password = get_password_hash(admin_password)
            admin_user = User(
                email=admin_email,
                password_hash=hashed_password
            )
            db.add(admin_user)
            db.commit()
            logger.info(f"Created admin user: {admin_email}")


@app.on_event("startup")
async def startup_event():
    global sync_service, ip_detector
    try:
        sync_service = SyncService()
    except ValueError as e:
        logger.error(f"Failed to initialise SyncService: {e}. Sync endpoints will be unavailable.")
    ip_detector = IPDetector()
    await create_admin_user()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Authentication endpoints
@app.post("/api/auth/login")
async def login(
    user_data: UserLogin,
    response: Response,
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": user.email})
    
    # Set HTTP-only cookie; COOKIE_SECURE env var controls the Secure flag
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        max_age=30 * 60  # 30 minutes
    )
    
    return {"message": "Login successful", "user": {"id": user.id, "email": user.email}}


@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="session_token")
    return {"message": "Logout successful"}


@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}


# Domain endpoints
@app.get("/api/domains", response_model=List[DomainSchema])
async def list_domains(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all registered domains"""
    return db.query(Domain).all()


@app.post("/api/domains", response_model=DomainSchema)
async def create_domain(
    domain_data: DomainCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register a new domain"""
    # Check if domain already exists
    existing = db.query(Domain).filter(Domain.name == domain_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domain {domain_data.name} is already registered"
        )

    # Create new domain
    new_domain = Domain(
        name=domain_data.name,
        zone_id=domain_data.zone_id
    )
    db.add(new_domain)
    db.commit()
    db.refresh(new_domain)

    logger.info(f"Created domain: {domain_data.name} with zone ID {domain_data.zone_id}")
    return new_domain


@app.put("/api/domains/{domain_id}", response_model=DomainSchema)
async def update_domain(
    domain_id: int,
    domain_data: DomainUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a domain"""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain with ID {domain_id} not found"
        )

    # Check for duplicate name if changing name
    if domain_data.name and domain_data.name != domain.name:
        existing = db.query(Domain).filter(Domain.name == domain_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Domain {domain_data.name} already exists"
            )
        domain.name = domain_data.name

    if domain_data.zone_id:
        domain.zone_id = domain_data.zone_id

    db.commit()
    db.refresh(domain)

    logger.info(f"Updated domain ID {domain_id}")
    return domain


@app.delete("/api/domains/{domain_id}")
async def delete_domain(
    domain_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a domain"""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain with ID {domain_id} not found"
        )

    # Check if domain has any records
    record_count = db.query(TrackedRecord).filter(TrackedRecord.domain_id == domain_id).count()
    if record_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete domain: {record_count} DNS record(s) are using it. Delete those records first."
        )

    db.delete(domain)
    db.commit()

    logger.info(f"Deleted domain ID {domain_id}")
    return {"message": f"Domain deleted successfully"}


# Records endpoints
@app.get("/api/records", response_model=List[TrackedRecordSchema])
async def list_records(
    domain: Optional[str] = None,
    fqdn: Optional[str] = None,
    record_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(TrackedRecord)
    
    if domain:
        query = query.filter(TrackedRecord.domain.ilike(f"%{domain}%"))
    if fqdn:
        query = query.filter(TrackedRecord.fqdn.ilike(f"%{fqdn}%"))
    if record_type:
        query = query.filter(TrackedRecord.type == record_type)
    
    return query.all()


@app.post("/api/records", response_model=TrackedRecordSchema)
async def create_record(
    record_data: TrackedRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # If domain_id is provided, get zone_identifier from the domain
    zone_identifier = record_data.zone_identifier
    if record_data.domain_id:
        domain = db.query(Domain).filter(Domain.id == record_data.domain_id).first()
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain with ID {record_data.domain_id} not found"
            )
        zone_identifier = domain.zone_id
        # Ensure the domain field matches the selected domain
        if record_data.domain != domain.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Domain field '{record_data.domain}' does not match selected domain '{domain.name}'"
            )

    # Compute FQDN from domain and host
    fqdn = record_data.domain if record_data.host == '@' else f"{record_data.host}.{record_data.domain}"

    # Check for duplicate
    existing = db.query(TrackedRecord).filter(
        and_(
            TrackedRecord.fqdn == fqdn,
            TrackedRecord.type == record_data.type
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{record_data.type} record for {fqdn} already exists"
        )

    # Create record with computed FQDN
    record_dict = record_data.dict()
    record_dict['fqdn'] = fqdn
    record_dict['zone_id_cached'] = zone_identifier  # Set zone_id_cached to zone_identifier for backward compatibility
    record_dict['zone_identifier'] = zone_identifier  # Also set zone_identifier

    db_record = TrackedRecord(**record_dict)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    # Immediately sync with Cloudflare
    try:
        sync_result = await sync_service.sync_single_record_immediate(db_record)
        if sync_result["status"] != "success":
            logger.warning(f"Failed to sync new record: {sync_result['message']}")
    except Exception as e:
        logger.error(f"Error syncing new record: {e}")

    return db_record


@app.put("/api/records/{record_id}", response_model=TrackedRecordSchema)
async def update_record(
    record_id: int,
    record_data: TrackedRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_record = db.query(TrackedRecord).filter(TrackedRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found"
        )
    
    # Update fields
    update_dict = record_data.dict(exclude_unset=True)
    
    # Track if domain or host changed to recompute FQDN
    domain_changed = 'domain' in update_dict or 'host' in update_dict
    
    for field, value in update_dict.items():
        setattr(db_record, field, value)
    
    # Recompute FQDN if domain or host changed, then check for duplicates
    if domain_changed:
        host = getattr(db_record, 'host', '@')
        domain = getattr(db_record, 'domain', '')
        new_fqdn = domain if host == '@' else f"{host}.{domain}"

        conflict = db.query(TrackedRecord).filter(
            and_(
                TrackedRecord.fqdn == new_fqdn,
                TrackedRecord.type == db_record.type,
                TrackedRecord.id != record_id
            )
        ).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{db_record.type} record for {new_fqdn} already exists"
            )

        db_record.fqdn = new_fqdn
    
    # Update zone_id_cached if zone_identifier changed
    if 'zone_identifier' in update_dict:
        db_record.zone_id_cached = update_dict['zone_identifier']
    
    db_record.updated_at = datetime.now()
    db.commit()
    db.refresh(db_record)
    
    # Immediately sync with Cloudflare
    try:
        sync_result = await sync_service.sync_single_record_immediate(db_record)
        if sync_result["status"] != "success":
            logger.warning(f"Failed to sync updated record: {sync_result['message']}")
    except Exception as e:
        logger.error(f"Error syncing updated record: {e}")
    
    return db_record


@app.delete("/api/records/{record_id}")
async def delete_record(
    record_id: int,
    delete_from_cloudflare: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_record = db.query(TrackedRecord).filter(TrackedRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found"
        )
    
    # Delete from Cloudflare if requested
    if delete_from_cloudflare and db_record.zone_id_cached:
        try:
            # Get existing records from Cloudflare
            records = await sync_service.cf_client.list_dns_records(
                db_record.zone_id_cached,
                db_record.type,
                db_record.fqdn
            )
            
            # Delete each matching record
            for cf_record in records:
                await sync_service.cf_client.delete_dns_record(
                    db_record.zone_id_cached,
                    cf_record["id"]
                )
                logger.info(f"Deleted {db_record.type} record for {db_record.fqdn} from Cloudflare")
                
        except Exception as e:
            logger.error(f"Error deleting record from Cloudflare: {e}")
            # Continue with local deletion even if Cloudflare deletion fails
    
    db.delete(db_record)
    db.commit()
    
    return {"message": "Record deleted successfully"}


# Sync endpoints
@app.post("/api/sync")
async def manual_sync(
    current_user: User = Depends(get_current_user)
):
    try:
        result = await sync_service.sync_all_records()
        return result
    except Exception as e:
        logger.error(f"Manual sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )


@app.get("/api/status", response_model=SyncStatus)
async def get_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    def get_setting(key: str, default: str = None) -> Optional[str]:
        setting = db.query(Setting).filter(Setting.key == key).first()
        return setting.value if setting else default
    
    return SyncStatus(
        last_seen_ipv4=get_setting("last_seen_ipv4"),
        last_seen_ipv6=get_setting("last_seen_ipv6"),
        last_sync_at=get_setting("last_sync_at"),
        last_sync_result=get_setting("last_sync_result")
    )


# Import endpoints
@app.post("/api/import")
async def import_records(
    import_data: ImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    results = {
        "dry_run": import_data.dry_run,
        "records_processed": 0,
        "records_created": 0,
        "records_failed": 0,
        "details": []
    }
    
    for import_record in import_data.records:
        result = {
            "domain": import_record.domain,
            "host": import_record.host,
            "ip_version": import_record.ip_version,
            "status": "error",
            "message": ""
        }
        
        try:
            # Map to tracked record format
            fqdn = f"{import_record.host}.{import_record.domain}" if import_record.host != "@" else import_record.domain
            record_type = "A" if import_record.ip_version == 4 else "AAAA"
            
            # Check for existing record
            existing = db.query(TrackedRecord).filter(
                and_(
                    TrackedRecord.fqdn == fqdn,
                    TrackedRecord.type == record_type
                )
            ).first()
            
            if existing:
                result["status"] = "skipped"
                result["message"] = "Record already exists"
            elif not import_data.dry_run:
                # Create new record
                new_record = TrackedRecord(
                    domain=import_record.domain,
                    fqdn=fqdn,
                    type=record_type,
                    proxied=import_record.proxied,
                    ttl=import_record.ttl
                )
                db.add(new_record)
                db.commit()
                db.refresh(new_record)
                
                result["status"] = "created"
                result["message"] = f"Created {record_type} record for {fqdn}"
                results["records_created"] += 1
                
                # Sync if requested
                if import_data.sync_after_import:
                    try:
                        sync_result = await sync_service.sync_single_record_immediate(new_record)
                        if sync_result["status"] == "success":
                            result["message"] += f" and synced to Cloudflare"
                        else:
                            result["message"] += f" but sync failed: {sync_result['message']}"
                    except Exception as e:
                        result["message"] += f" but sync failed: {str(e)}"
            else:
                result["status"] = "would_create"
                result["message"] = f"Would create {record_type} record for {fqdn}"
                
            results["records_processed"] += 1
            
        except Exception as e:
            result["message"] = f"Error: {str(e)}"
            results["records_failed"] += 1
        
        results["details"].append(result)
    
    return results


# Audit endpoints
@app.get("/api/audit", response_model=List[AuditEntry])
async def get_audit_log(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(AuditLog).order_by(AuditLog.ts.desc()).offset(offset).limit(limit).all()


# Settings endpoints
@app.get("/api/settings/{key}")
async def get_setting(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    setting = db.query(Setting).filter(Setting.key == key).first()
    
    # Define default values for known settings
    defaults = {
        "ipv6_enabled": "false",
        "poll_interval_seconds": "300",
        "discord_webhook_url": ""
    }
    
    if not setting:
        # Return default value if setting doesn't exist
        default_value = defaults.get(key, "")
        return {"key": key, "value": default_value}
    
    return {"key": setting.key, "value": setting.value}


@app.put("/api/settings/{key}")
async def update_setting(
    key: str,
    setting_data: SettingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = setting_data.value
    else:
        setting = Setting(key=key, value=setting_data.value)
        db.add(setting)
    
    db.commit()
    return {"key": setting.key, "value": setting.value}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)