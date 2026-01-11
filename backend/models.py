from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())


class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)  # e.g., dreadnought.work
    zone_id = Column(String, nullable=False, index=True)  # Cloudflare Zone ID
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship to tracked records
    records = relationship("TrackedRecord", back_populates="domain_obj")


class TrackedRecord(Base):
    __tablename__ = "tracked_records"

    id = Column(Integer, primary_key=True, index=True)
    # Domain relationship
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=True, index=True)
    # New fields - temporarily nullable for migration
    zone_identifier = Column(String, nullable=True, index=True)  # Cloudflare Zone ID
    host = Column(String, nullable=True, index=True)  # Host part (e.g., zabbix, @ for root)
    # Existing fields
    domain = Column(String, nullable=False, index=True)  # Base domain (e.g., darkspace.pro)
    fqdn = Column(String, nullable=False, index=True)  # Computed FQDN
    type = Column(String, nullable=False)  # A or AAAA
    proxied = Column(Boolean, default=False)
    ttl = Column(Integer, default=300)
    zone_id_cached = Column(String, nullable=True)  # Keep for backward compatibility
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship to domain
    domain_obj = relationship("Domain", back_populates="records")


class Setting(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime, default=func.now())
    action = Column(String, nullable=False)
    details = Column(JSON, nullable=True)