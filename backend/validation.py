import re
from typing import Optional
from fastapi import HTTPException, status


def validate_domain(domain: str) -> str:
    """Validate domain format"""
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain cannot be empty"
        )
    
    # Basic domain validation
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    if not re.match(domain_pattern, domain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid domain format"
        )
    
    if len(domain) > 253:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain name too long"
        )
    
    return domain.lower()


def validate_fqdn(fqdn: str, domain: Optional[str] = None) -> str:
    """Validate FQDN format and relationship to domain"""
    if not fqdn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FQDN cannot be empty"
        )
    
    # Basic FQDN validation
    fqdn_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    if not re.match(fqdn_pattern, fqdn):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid FQDN format"
        )
    
    if len(fqdn) > 253:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FQDN too long"
        )
    
    # Check if FQDN belongs to domain
    if domain:
        domain_lower = domain.lower()
        fqdn_lower = fqdn.lower()
        
        if fqdn_lower != domain_lower and not fqdn_lower.endswith(f".{domain_lower}"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FQDN '{fqdn}' must belong to domain '{domain}'"
            )
    
    return fqdn.lower()


def validate_ttl(ttl: int, proxied: bool = False) -> int:
    """Validate TTL value"""
    if proxied:
        return 1  # Force Auto TTL for proxied records
    
    if ttl < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TTL must be at least 1 second"
        )
    
    if ttl > 86400:  # 24 hours
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TTL cannot exceed 86400 seconds (24 hours)"
        )
    
    return ttl


def validate_record_type(record_type: str) -> str:
    """Validate DNS record type"""
    valid_types = ["A", "AAAA"]
    if record_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Record type must be one of: {', '.join(valid_types)}"
        )
    
    return record_type


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize string input"""
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Value must be a string"
        )
    
    # Remove null bytes and control characters
    sanitized = ''.join(char for char in value if ord(char) >= 32 or char == '\n' or char == '\t')
    
    if len(sanitized) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"String too long (max {max_length} characters)"
        )
    
    return sanitized.strip()


def validate_email(email: str) -> str:
    """Validate email format"""
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email cannot be empty"
        )
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    if len(email) > 254:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email too long"
        )
    
    return email.lower()


def validate_password(password: str) -> str:
    """Validate password strength"""
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be empty"
        )
    
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    if len(password) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password too long"
        )
    
    return password