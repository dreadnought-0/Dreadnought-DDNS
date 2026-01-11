import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from cf_client import CloudflareClient, CloudflareError


@pytest.fixture
def cf_client():
    return CloudflareClient(api_token="test_token")


@pytest.mark.asyncio
async def test_make_request_success(cf_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "result": {"id": "test"}}
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)
        
        result = await cf_client._make_request("GET", "/test")
        assert result["success"] == True
        assert result["result"]["id"] == "test"


@pytest.mark.asyncio
async def test_make_request_rate_limited(cf_client):
    # First response is rate limited
    mock_rate_limited_response = MagicMock()
    mock_rate_limited_response.status_code = 429
    mock_rate_limited_response.headers = {"Retry-After": "1"}
    
    # Second response is successful
    mock_success_response = MagicMock()
    mock_success_response.status_code = 200
    mock_success_response.json.return_value = {"success": True, "result": {"id": "test"}}
    
    with patch("httpx.AsyncClient") as mock_client, \
         patch("asyncio.sleep") as mock_sleep:
        
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(
            side_effect=[mock_rate_limited_response, mock_success_response]
        )
        
        result = await cf_client._make_request("GET", "/test")
        assert result["success"] == True
        mock_sleep.assert_called()


@pytest.mark.asyncio
async def test_make_request_api_error(cf_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "success": False,
        "errors": [{"message": "Invalid request"}]
    }
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)
        
        with pytest.raises(CloudflareError) as exc_info:
            await cf_client._make_request("GET", "/test")
        
        assert "Invalid request" in str(exc_info.value)


@pytest.mark.asyncio
async def test_list_zones(cf_client):
    mock_response = {
        "success": True,
        "result": [
            {"id": "zone1", "name": "example.com"},
            {"id": "zone2", "name": "test.com"}
        ]
    }
    
    with patch.object(cf_client, '_make_request', return_value=mock_response) as mock_request:
        zones = await cf_client.list_zones()
        assert len(zones) == 2
        assert zones[0]["name"] == "example.com"
        mock_request.assert_called_once_with("GET", "/zones", params={})


@pytest.mark.asyncio
async def test_list_zones_with_name(cf_client):
    mock_response = {
        "success": True,
        "result": [{"id": "zone1", "name": "example.com"}]
    }
    
    with patch.object(cf_client, '_make_request', return_value=mock_response) as mock_request:
        zones = await cf_client.list_zones("example.com")
        assert len(zones) == 1
        mock_request.assert_called_once_with("GET", "/zones", params={"name": "example.com"})


@pytest.mark.asyncio
async def test_get_zone_id(cf_client):
    mock_response = {
        "success": True,
        "result": [{"id": "zone123", "name": "example.com"}]
    }
    
    with patch.object(cf_client, '_make_request', return_value=mock_response):
        zone_id = await cf_client.get_zone_id("example.com")
        assert zone_id == "zone123"


@pytest.mark.asyncio
async def test_get_zone_id_not_found(cf_client):
    mock_response = {
        "success": True,
        "result": []
    }
    
    with patch.object(cf_client, '_make_request', return_value=mock_response):
        zone_id = await cf_client.get_zone_id("nonexistent.com")
        assert zone_id is None


@pytest.mark.asyncio
async def test_create_dns_record(cf_client):
    mock_response = {
        "success": True,
        "result": {
            "id": "record123",
            "type": "A",
            "name": "test.example.com",
            "content": "1.2.3.4",
            "proxied": False,
            "ttl": 300
        }
    }
    
    with patch.object(cf_client, '_make_request', return_value=mock_response) as mock_request:
        result = await cf_client.create_dns_record(
            "zone123", "A", "test.example.com", "1.2.3.4", False, 300
        )
        
        assert result["id"] == "record123"
        mock_request.assert_called_once()
        
        # Check the request data
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/zones/zone123/dns_records"
        
        json_data = call_args[1]["json_data"]
        assert json_data["type"] == "A"
        assert json_data["name"] == "test.example.com"
        assert json_data["content"] == "1.2.3.4"
        assert json_data["proxied"] == False
        assert json_data["ttl"] == 300


@pytest.mark.asyncio
async def test_create_dns_record_proxied_forces_auto_ttl(cf_client):
    mock_response = {
        "success": True,
        "result": {"id": "record123"}
    }
    
    with patch.object(cf_client, '_make_request', return_value=mock_response) as mock_request:
        await cf_client.create_dns_record(
            "zone123", "A", "test.example.com", "1.2.3.4", True, 3600
        )
        
        # Should force TTL to 1 (Auto) for proxied records
        call_args = mock_request.call_args
        json_data = call_args[1]["json_data"]
        assert json_data["ttl"] == 1
        assert json_data["proxied"] == True


@pytest.mark.asyncio
async def test_upsert_dns_record_create(cf_client):
    # Mock list_dns_records to return empty (no existing record)
    mock_list_response = {"success": True, "result": []}
    
    # Mock create_dns_record response
    mock_create_response = {
        "success": True,
        "result": {"id": "record123", "type": "A", "name": "test.example.com"}
    }
    
    with patch.object(cf_client, '_make_request', side_effect=[mock_list_response, mock_create_response]):
        result, action = await cf_client.upsert_dns_record(
            "zone123", "A", "test.example.com", "1.2.3.4", False, 300
        )
        
        assert action == "created"
        assert result["id"] == "record123"


@pytest.mark.asyncio
async def test_upsert_dns_record_update(cf_client):
    # Mock list_dns_records to return existing record
    mock_list_response = {
        "success": True,
        "result": [{"id": "existing123", "type": "A", "name": "test.example.com"}]
    }
    
    # Mock update_dns_record response
    mock_update_response = {
        "success": True,
        "result": {"id": "existing123", "type": "A", "name": "test.example.com"}
    }
    
    with patch.object(cf_client, '_make_request', side_effect=[mock_list_response, mock_update_response]):
        result, action = await cf_client.upsert_dns_record(
            "zone123", "A", "test.example.com", "1.2.3.4", False, 300
        )
        
        assert action == "updated"
        assert result["id"] == "existing123"


@pytest.mark.asyncio
async def test_timeout_handling(cf_client):
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )
        
        with pytest.raises(CloudflareError) as exc_info:
            await cf_client._make_request("GET", "/test")
        
        assert "timeout" in str(exc_info.value).lower()