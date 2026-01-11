from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from validation import validate_domain, validate_fqdn, validate_ttl, validate_email, validate_password


class RecordType(str, Enum):
    A = "A"
    AAAA = "AAAA"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    
    @validator('email')
    def validate_email_format(cls, v):
        return validate_email(v)
    
    @validator('password')
    def validate_password_strength(cls, v):
        return validate_password(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
    @validator('email')
    def validate_email_format(cls, v):
        return validate_email(v)


class User(BaseModel):
    id: int
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class TrackedRecordBase(BaseModel):
    zone_identifier: Optional[str] = Field(None, description="Cloudflare Zone ID (deprecated, use domain_id)")
    domain_id: Optional[int] = Field(None, description="Domain ID from registered domains")
    domain: str = Field(..., description="Base domain (e.g., darkspace.pro)")
    host: str = Field(..., description="Host part (e.g., zabbix, @ for root domain)")
    type: RecordType
    proxied: bool = Field(default=False)
    ttl: int = Field(default=300, ge=1)

    @validator('domain')
    def validate_domain_format(cls, v):
        return validate_domain(v)

    @validator('zone_identifier')
    def validate_zone_identifier(cls, v):
        if v is None:
            return v
        # Basic validation for Cloudflare zone ID format (32 hex characters)
        if not v or len(v) != 32 or not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError('Zone identifier must be a 32-character hexadecimal string')
        return v.lower()

    @validator('host')
    def validate_host_format(cls, v):
        if not v:
            raise ValueError('Host cannot be empty')
        # Allow @ for root domain, otherwise validate as subdomain
        if v != '@' and not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Host must contain only alphanumeric characters, hyphens, and underscores')
        return v

    @validator('ttl')
    def validate_ttl_value(cls, v, values):
        proxied = values.get('proxied', False)
        return validate_ttl(v, proxied)


class TrackedRecordCreate(TrackedRecordBase):
    @validator('domain_id')
    def validate_domain_or_zone(cls, v, values):
        zone_id = values.get('zone_identifier')
        if not v and not zone_id:
            raise ValueError('Either domain_id or zone_identifier must be provided')
        return v


class TrackedRecordUpdate(BaseModel):
    zone_identifier: Optional[str] = None
    domain: Optional[str] = None
    host: Optional[str] = None
    type: Optional[RecordType] = None
    proxied: Optional[bool] = None
    ttl: Optional[int] = None


class TrackedRecord(BaseModel):
    id: int
    zone_identifier: Optional[str] = None  # Nullable for backward compatibility
    domain: str
    host: Optional[str] = None  # Nullable for backward compatibility
    fqdn: str
    type: RecordType
    proxied: bool = False
    ttl: int = 300
    zone_id_cached: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SyncStatus(BaseModel):
    last_seen_ipv4: Optional[str] = None
    last_seen_ipv6: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    last_sync_result: Optional[str] = None


class AuditEntry(BaseModel):
    id: int
    ts: datetime
    action: str
    details: Optional[dict] = None
    
    class Config:
        from_attributes = True


class ImportRecord(BaseModel):
    domain: str
    host: str
    ip_version: int = Field(..., description="4 or 6")
    ttl: int = Field(default=300)
    proxied: bool = Field(default=False)


class ImportRequest(BaseModel):
    records: List[ImportRecord]
    dry_run: bool = Field(default=True)
    sync_after_import: bool = Field(default=False)


class SettingUpdate(BaseModel):
    value: str


class DomainCreate(BaseModel):
    name: str = Field(..., description="Domain name (e.g., dreadnought.work)")
    zone_id: str = Field(..., description="Cloudflare Zone ID")

    @validator('name')
    def validate_domain_format(cls, v):
        return validate_domain(v)

    @validator('zone_id')
    def validate_zone_id_format(cls, v):
        # Basic validation for Cloudflare zone ID format (32 hex characters)
        if not v or len(v) != 32 or not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError('Zone ID must be a 32-character hexadecimal string')
        return v.lower()


class DomainUpdate(BaseModel):
    name: Optional[str] = None
    zone_id: Optional[str] = None

    @validator('name')
    def validate_domain_format(cls, v):
        if v is not None:
            return validate_domain(v)
        return v

    @validator('zone_id')
    def validate_zone_id_format(cls, v):
        if v is not None:
            if not v or len(v) != 32 or not all(c in '0123456789abcdef' for c in v.lower()):
                raise ValueError('Zone ID must be a 32-character hexadecimal string')
            return v.lower()
        return v


class Domain(BaseModel):
    id: int
    name: str
    zone_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True