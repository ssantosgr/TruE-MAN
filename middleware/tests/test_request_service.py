"""Unit tests for request_service module."""
import pytest
import json
from unittest.mock import patch, MagicMock
from services.request_service import (
    validate_create_request_data,
    extract_and_save_request_data,
    forward_to_node_server,
    create_request_handler
)


class TestValidateCreateRequestData:
    """Tests for request data validation."""
    
    def test_valid_data(self):
        """Test validation with all required fields present."""
        data = {
            "privateKey": "0xtest",
            "contractAddress": "0xcontract",
            "sharedTAC": "1234",
            "ueImsis": ["001010000000001"]
        }
        
        valid, error = validate_create_request_data(data)
        assert valid is True
        assert error is None
    
    def test_missing_private_key(self):
        """Test validation fails when privateKey is missing."""
        data = {
            "contractAddress": "0xcontract",
            "sharedTAC": "1234",
            "ueImsis": ["001010000000001"]
        }
        
        valid, error = validate_create_request_data(data)
        assert valid is False
        assert "Missing" in error
    
    def test_missing_contract_address(self):
        """Test validation fails when contractAddress is missing."""
        data = {
            "privateKey": "0xtest",
            "sharedTAC": "1234",
            "ueImsis": ["001010000000001"]
        }
        
        valid, error = validate_create_request_data(data)
        assert valid is False
        assert "Missing" in error
    
    def test_missing_shared_tac(self):
        """Test validation fails when sharedTAC is missing."""
        data = {
            "privateKey": "0xtest",
            "contractAddress": "0xcontract",
            "ueImsis": ["001010000000001"]
        }
        
        valid, error = validate_create_request_data(data)
        assert valid is False
        assert "Missing" in error
    
    def test_missing_ue_imsis(self):
        """Test validation fails when ueImsis is missing."""
        data = {
            "privateKey": "0xtest",
            "contractAddress": "0xcontract",
            "sharedTAC": "1234"
        }
        
        valid, error = validate_create_request_data(data)
        assert valid is False
        assert "Missing" in error
    
    def test_empty_data(self):
        """Test validation fails with empty data."""
        valid, error = validate_create_request_data(None)
        assert valid is False
        assert "No JSON data" in error


class TestExtractAndSaveRequestData:
    """Tests for extracting and saving request data."""
    
    @patch('services.request_service.save_request')
    @patch('services.request_service.uuid.uuid4')
    def test_extracts_all_fields(self, mock_uuid, mock_save):
        """Test that all fields are properly extracted and saved."""
        mock_uuid.return_value = MagicMock(return_value='test-uuid-123')
        mock_uuid.return_value.__str__ = MagicMock(return_value='test-uuid-123')
        
        data = {
            "privateKey": "0xtest",
            "contractAddress": "0xcontract",
            "sharedTAC": "1234",
            "ueImsis": ["001010000000001", "001010000000002"],
            "durationMins": 60,
            "tenantPLMN": "00101",
            "tenantAMFIP": "192.168.1.1",
            "tenantAMFPort": 38412,
            "tenantNSSAI": [{"sst": 1, "sd": "010203"}]
        }
        
        request_id, ue_imsis = extract_and_save_request_data(data)
        
        assert request_id == 'test-uuid-123'
        assert ue_imsis == ["001010000000001", "001010000000002"]
        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        assert call_kwargs['private_key'] == "0xtest"
        assert call_kwargs['shared_tac'] == "1234"
        assert call_kwargs['duration_mins'] == 60
    
    @patch('services.request_service.save_request')
    @patch('services.request_service.uuid.uuid4')
    def test_handles_optional_fields(self, mock_uuid, mock_save):
        """Test handling of optional fields."""
        mock_uuid.return_value = MagicMock(return_value='test-uuid-456')
        mock_uuid.return_value.__str__ = MagicMock(return_value='test-uuid-456')
        
        data = {
            "privateKey": "0xtest",
            "contractAddress": "0xcontract",
            "sharedTAC": "5678",
            "ueImsis": ["001010000000003"]
        }
        
        request_id, ue_imsis = extract_and_save_request_data(data)
        
        assert request_id == 'test-uuid-456'
        assert ue_imsis == ["001010000000003"]
        mock_save.assert_called_once()


class TestForwardToNodeServer:
    """Tests for forwarding requests to Node.js server."""
    
    @patch('services.request_service.requests.post')
    def test_successful_forward(self, mock_post):
        """Test successful request forwarding."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"requestId": "0xhash123"}
        mock_post.return_value = mock_response
        
        external_id, response_data = forward_to_node_server(
            "0xprivatekey",
            "0xcontract",
            ["imsi1", "imsi2"],
            60,
            "http://localhost:3020/api"
        )
        
        assert external_id == "0xhash123"
        assert response_data["requestId"] == "0xhash123"
        mock_post.assert_called_once()
    
    @patch('services.request_service.requests.post')
    def test_node_server_failure(self, mock_post):
        """Test handling of Node.js server failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            forward_to_node_server(
                "0xprivatekey",
                "0xcontract",
                ["imsi1"],
                60,
                "http://localhost:3020/api"
            )
        
        assert "Failed to process request" in str(exc_info.value)
    
    @patch('services.request_service.requests.post')
    def test_missing_request_id_in_response(self, mock_post):
        """Test handling when Node.js returns 200 but no requestId."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "success"}
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            forward_to_node_server(
                "0xprivatekey",
                "0xcontract",
                ["imsi1"],
                60,
                "http://localhost:3020/api"
            )
        
        assert "No request ID received" in str(exc_info.value)


class TestCreateRequestHandler:
    """Tests for the main request handler."""
    
    @patch('services.request_service.save_request')
    @patch('services.request_service.forward_to_node_server')
    @patch('services.request_service.extract_and_save_request_data')
    def test_successful_request_creation(self, mock_extract, mock_forward, mock_save):
        """Test complete successful request creation flow."""
        mock_extract.return_value = ('req-id-123', ['imsi1', 'imsi2'])
        mock_forward.return_value = ('0xhash123', {"requestId": "0xhash123"})
        
        data = {
            "privateKey": "0xtest",
            "contractAddress": "0xcontract",
            "sharedTAC": "1234",
            "ueImsis": ["imsi1", "imsi2"]
        }
        
        response_data, error, status_code = create_request_handler(
            data,
            "http://localhost:3020/api"
        )
        
        assert error is None
        assert status_code == 200
        assert response_data["requestId"] == "0xhash123"
        mock_save.assert_called_once()
    
    def test_validation_failure(self):
        """Test request creation with invalid data."""
        data = {
            "privateKey": "0xtest"
            # Missing required fields
        }
        
        response_data, error, status_code = create_request_handler(
            data,
            "http://localhost:3020/api"
        )
        
        assert response_data is None
        assert error is not None
        assert status_code == 400
        assert "Missing" in error
    
    @patch('services.request_service.extract_and_save_request_data')
    @patch('services.request_service.requests.post')
    def test_connection_error(self, mock_post, mock_extract):
        """Test handling of connection errors."""
        import requests as req_module
        mock_extract.return_value = ('req-id-456', ['imsi1'])
        mock_post.side_effect = req_module.exceptions.ConnectionError()
        
        data = {
            "privateKey": "0xtest",
            "contractAddress": "0xcontract",
            "sharedTAC": "1234",
            "ueImsis": ["imsi1"]
        }
        
        response_data, error, status_code = create_request_handler(
            data,
            "http://localhost:3020/api"
        )
        
        assert response_data is None
        assert error == "Failed to forward request"
        assert status_code == 500
