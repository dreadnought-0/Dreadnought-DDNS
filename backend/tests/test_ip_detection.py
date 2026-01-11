import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from ip_detection import IPDetector


@pytest.fixture
def ip_detector():
    return IPDetector(ipv6_enabled=True)


@pytest.fixture
def ipv4_only_detector():
    return IPDetector(ipv6_enabled=False)


@pytest.mark.asyncio
async def test_fetch_ip_from_endpoint_success(ip_detector):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "192.168.1.1"
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        ip = await ip_detector._fetch_ip_from_endpoint("https://api.ipify.org")
        assert ip == "192.168.1.1"


@pytest.mark.asyncio
async def test_fetch_ip_from_endpoint_invalid_response(ip_detector):
    mock_response = MagicMock()
    mock_response.status_code = 404
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        ip = await ip_detector._fetch_ip_from_endpoint("https://api.ipify.org")
        assert ip is None


@pytest.mark.asyncio
async def test_fetch_ip_from_endpoint_timeout(ip_detector):
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )
        
        ip = await ip_detector._fetch_ip_from_endpoint("https://api.ipify.org")
        assert ip is None


def test_is_valid_ip_ipv4(ip_detector):
    assert ip_detector._is_valid_ip("192.168.1.1") == True
    assert ip_detector._is_valid_ip("8.8.8.8") == True
    assert ip_detector._is_valid_ip("127.0.0.1") == True
    assert ip_detector._is_valid_ip("256.1.1.1") == False
    assert ip_detector._is_valid_ip("192.168.1") == False
    assert ip_detector._is_valid_ip("invalid") == False


def test_is_valid_ip_ipv6(ip_detector):
    assert ip_detector._is_valid_ip("2001:db8::1") == True
    assert ip_detector._is_valid_ip("::1") == True
    assert ip_detector._is_valid_ip("fe80::1") == True
    assert ip_detector._is_valid_ip("2001:db8:85a3::8a2e:370:7334") == True
    assert ip_detector._is_valid_ip("invalid::address") == False


@pytest.mark.asyncio
async def test_get_ipv4_success(ip_detector):
    # Mock successful response from first endpoint
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "203.0.113.1"
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        ip = await ip_detector.get_ipv4()
        assert ip == "203.0.113.1"


@pytest.mark.asyncio
async def test_get_ipv4_fallback_to_second_endpoint(ip_detector):
    # Mock first endpoint failure, second endpoint success
    mock_failed_response = MagicMock()
    mock_failed_response.status_code = 500
    
    mock_success_response = MagicMock()
    mock_success_response.status_code = 200
    mock_success_response.text = "203.0.113.2"
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=[mock_failed_response, mock_success_response]
        )
        
        ip = await ip_detector.get_ipv4()
        assert ip == "203.0.113.2"


@pytest.mark.asyncio
async def test_get_ipv4_all_endpoints_fail(ip_detector):
    with patch.object(ip_detector, '_fetch_ip_from_endpoint', return_value=None):
        ip = await ip_detector.get_ipv4()
        assert ip is None


@pytest.mark.asyncio
async def test_get_ipv6_success(ip_detector):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "2001:db8::1"
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        
        ip = await ip_detector.get_ipv6()
        assert ip == "2001:db8::1"


@pytest.mark.asyncio
async def test_get_ipv6_disabled(ipv4_only_detector):
    ip = await ipv4_only_detector.get_ipv6()
    assert ip is None


@pytest.mark.asyncio
async def test_get_current_ips_both_success(ip_detector):
    with patch.object(ip_detector, 'get_ipv4', return_value="203.0.113.1"), \
         patch.object(ip_detector, 'get_ipv6', return_value="2001:db8::1"):
        
        ipv4, ipv6 = await ip_detector.get_current_ips()
        assert ipv4 == "203.0.113.1"
        assert ipv6 == "2001:db8::1"


@pytest.mark.asyncio
async def test_get_current_ips_ipv4_only(ipv4_only_detector):
    with patch.object(ipv4_only_detector, 'get_ipv4', return_value="203.0.113.1"):
        ipv4, ipv6 = await ipv4_only_detector.get_current_ips()
        assert ipv4 == "203.0.113.1"
        assert ipv6 is None


@pytest.mark.asyncio
async def test_get_current_ips_with_exceptions(ip_detector):
    with patch.object(ip_detector, 'get_ipv4', side_effect=Exception("Network error")), \
         patch.object(ip_detector, 'get_ipv6', return_value="2001:db8::1"):
        
        ipv4, ipv6 = await ip_detector.get_current_ips()
        assert ipv4 is None  # Exception handled
        assert ipv6 == "2001:db8::1"