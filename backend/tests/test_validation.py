import pytest
from fastapi import HTTPException

from validation import (
    validate_domain,
    validate_fqdn,
    validate_ttl,
    validate_record_type,
    validate_email,
    validate_password,
    sanitize_string
)


class TestDomainValidation:
    def test_valid_domains(self):
        assert validate_domain("example.com") == "example.com"
        assert validate_domain("sub.example.com") == "sub.example.com"
        assert validate_domain("test-domain.co.uk") == "test-domain.co.uk"
        assert validate_domain("EXAMPLE.COM") == "example.com"  # Should lowercase
    
    def test_empty_domain(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_domain("")
        assert exc_info.value.status_code == 400
    
    def test_invalid_domain_format(self):
        with pytest.raises(HTTPException):
            validate_domain("invalid..domain")
        with pytest.raises(HTTPException):
            validate_domain("-invalid.com")
        with pytest.raises(HTTPException):
            validate_domain("invalid-.com")
    
    def test_domain_too_long(self):
        long_domain = "a" * 250 + ".com"
        with pytest.raises(HTTPException):
            validate_domain(long_domain)


class TestFQDNValidation:
    def test_valid_fqdns(self):
        assert validate_fqdn("example.com") == "example.com"
        assert validate_fqdn("sub.example.com") == "sub.example.com"
        assert validate_fqdn("EXAMPLE.COM") == "example.com"  # Should lowercase
    
    def test_fqdn_belongs_to_domain(self):
        assert validate_fqdn("sub.example.com", "example.com") == "sub.example.com"
        assert validate_fqdn("example.com", "example.com") == "example.com"
    
    def test_fqdn_does_not_belong_to_domain(self):
        with pytest.raises(HTTPException):
            validate_fqdn("other.com", "example.com")
        with pytest.raises(HTTPException):
            validate_fqdn("sub.other.com", "example.com")
    
    def test_empty_fqdn(self):
        with pytest.raises(HTTPException):
            validate_fqdn("")
    
    def test_invalid_fqdn_format(self):
        with pytest.raises(HTTPException):
            validate_fqdn("invalid..fqdn")


class TestTTLValidation:
    def test_valid_ttl(self):
        assert validate_ttl(300) == 300
        assert validate_ttl(1) == 1
        assert validate_ttl(86400) == 86400
    
    def test_proxied_forces_auto_ttl(self):
        assert validate_ttl(3600, proxied=True) == 1
        assert validate_ttl(300, proxied=True) == 1
    
    def test_ttl_too_low(self):
        with pytest.raises(HTTPException):
            validate_ttl(0)
        with pytest.raises(HTTPException):
            validate_ttl(-1)
    
    def test_ttl_too_high(self):
        with pytest.raises(HTTPException):
            validate_ttl(86401)


class TestRecordTypeValidation:
    def test_valid_types(self):
        assert validate_record_type("A") == "A"
        assert validate_record_type("AAAA") == "AAAA"
    
    def test_invalid_types(self):
        with pytest.raises(HTTPException):
            validate_record_type("CNAME")
        with pytest.raises(HTTPException):
            validate_record_type("MX")
        with pytest.raises(HTTPException):
            validate_record_type("invalid")


class TestEmailValidation:
    def test_valid_emails(self):
        assert validate_email("test@example.com") == "test@example.com"
        assert validate_email("user.name+tag@example.co.uk") == "user.name+tag@example.co.uk"
        assert validate_email("TEST@EXAMPLE.COM") == "test@example.com"  # Should lowercase
    
    def test_empty_email(self):
        with pytest.raises(HTTPException):
            validate_email("")
    
    def test_invalid_email_format(self):
        with pytest.raises(HTTPException):
            validate_email("invalid")
        with pytest.raises(HTTPException):
            validate_email("invalid@")
        with pytest.raises(HTTPException):
            validate_email("@invalid.com")
        with pytest.raises(HTTPException):
            validate_email("invalid@invalid")
    
    def test_email_too_long(self):
        long_email = "a" * 250 + "@example.com"
        with pytest.raises(HTTPException):
            validate_email(long_email)


class TestPasswordValidation:
    def test_valid_passwords(self):
        assert validate_password("password123") == "password123"
        assert validate_password("VerySecurePassword!@#$") == "VerySecurePassword!@#$"
    
    def test_empty_password(self):
        with pytest.raises(HTTPException):
            validate_password("")
    
    def test_password_too_short(self):
        with pytest.raises(HTTPException):
            validate_password("short")
        with pytest.raises(HTTPException):
            validate_password("1234567")  # 7 characters
    
    def test_password_too_long(self):
        long_password = "a" * 129
        with pytest.raises(HTTPException):
            validate_password(long_password)


class TestSanitizeString:
    def test_valid_string(self):
        assert sanitize_string("normal string") == "normal string"
        assert sanitize_string("  trimmed  ") == "trimmed"
    
    def test_string_with_control_characters(self):
        dirty_string = "text\x00with\x01control\x02chars"
        clean_string = sanitize_string(dirty_string)
        assert "\x00" not in clean_string
        assert "\x01" not in clean_string
        assert "\x02" not in clean_string
        assert "textwithcontrolchars" == clean_string
    
    def test_string_too_long(self):
        long_string = "a" * 256
        with pytest.raises(HTTPException):
            sanitize_string(long_string, max_length=255)
    
    def test_non_string_input(self):
        with pytest.raises(HTTPException):
            sanitize_string(123)