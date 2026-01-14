"""Unit tests for state_service module."""
import pytest
from unittest.mock import patch, MagicMock
from services.state_service import (
    validate_state,
    handle_non_accepted_state,
    handle_accepted_state,
    update_request_state_handler
)


class TestValidateState:
    """Tests for state validation."""
    
    def test_valid_accepted_state(self):
        """Test validation with accepted state."""
        valid, error = validate_state('accepted')
        assert valid is True
        assert error is None
    
    def test_valid_rejected_state(self):
        """Test validation with rejected state."""
        valid, error = validate_state('rejected')
        assert valid is True
        assert error is None
    
    def test_valid_completed_state(self):
        """Test validation with completed state."""
        valid, error = validate_state('completed')
        assert valid is True
        assert error is None
    
    def test_case_insensitive_validation(self):
        """Test that state validation is case-insensitive."""
        valid, error = validate_state('ACCEPTED')
        assert valid is True
        assert error is None
        
        valid, error = validate_state('Rejected')
        assert valid is True
        assert error is None
    
    def test_invalid_state(self):
        """Test validation with invalid state."""
        valid, error = validate_state('invalid')
        assert valid is False
        assert 'Invalid state' in error
        assert 'accepted' in error
        assert 'rejected' in error
        assert 'completed' in error


class TestHandleNonAcceptedState:
    """Tests for handling rejected/completed states."""
    
    @patch('services.state_service.save_request')
    def test_handle_rejected_state(self, mock_save):
        """Test handling of rejected state."""
        result = handle_non_accepted_state(
            'req-id-123',
            '0xhash123',
            'rejected'
        )
        
        assert result is True
        mock_save.assert_called_once_with('req-id-123', state='Rejected')
    
    @patch('services.state_service.save_request')
    def test_handle_completed_state(self, mock_save):
        """Test handling of completed state."""
        result = handle_non_accepted_state(
            'req-id-456',
            '0xhash456',
            'completed'
        )
        
        assert result is True
        mock_save.assert_called_once_with('req-id-456', state='Completed')


class TestHandleAcceptedState:
    """Tests for handling accepted state."""
    
    @patch('services.state_service.schedule_configuration_restoration')
    @patch('services.state_service.get_and_update_ue_restrictions')
    @patch('services.state_service.restart_agent_with_tenant_config')
    @patch('services.state_service.get_request_data_by_external_requestId')
    @patch('services.state_service.save_request')
    def test_successful_acceptance(self, mock_save, mock_get_data, mock_restart,
                                   mock_update_ues, mock_schedule):
        """Test successful request acceptance."""
        mock_get_data.return_value = {
            'tenant_nssai_json': None,
            'tenant_amf_ip': '192.168.1.1',
            'tenant_amf_port': 38412,
            'tenant_plmn': '00101',
            'shared_tac': '1234',
            'duration_mins': 60
        }
        mock_restart.return_value = True
        mock_update_ues.return_value = (True, [{"imsi": "test"}], 1)
        
        success, error = handle_accepted_state(
            'req-id-123',
            '0xhash123',
            'http://agent:4000'
        )
        
        assert success is True
        assert error is None
        mock_restart.assert_called_once()
        mock_update_ues.assert_called_once()
        mock_save.assert_called_with('req-id-123', state='Completed')
        mock_schedule.assert_called_once()
    
    @patch('services.state_service.get_request_data_by_external_requestId')
    def test_request_data_not_found(self, mock_get_data):
        """Test handling when request data is not found."""
        mock_get_data.return_value = None
        
        success, error = handle_accepted_state(
            'req-id-123',
            '0xhash123',
            'http://agent:4000'
        )
        
        assert success is False
        assert "Failed to retrieve request data" in error
    
    @patch('services.state_service.restart_agent_with_tenant_config')
    @patch('services.state_service.get_request_data_by_external_requestId')
    def test_agent_restart_failure(self, mock_get_data, mock_restart):
        """Test handling of agent restart failure."""
        mock_get_data.return_value = {
            'tenant_nssai_json': None,
            'tenant_amf_ip': None,
            'tenant_amf_port': None,
            'tenant_plmn': '00101',
            'shared_tac': '1234',
            'duration_mins': 60
        }
        mock_restart.return_value = False
        
        success, error = handle_accepted_state(
            'req-id-123',
            '0xhash123',
            'http://agent:4000'
        )
        
        assert success is False
        assert "Failed to restart service on agent" in error
    
    @patch('services.state_service.get_and_update_ue_restrictions')
    @patch('services.state_service.restart_agent_with_tenant_config')
    @patch('services.state_service.get_request_data_by_external_requestId')
    @patch('services.state_service.save_request')
    def test_ue_update_failure(self, mock_save, mock_get_data, mock_restart, mock_update_ues):
        """Test handling of UE update failure."""
        mock_get_data.return_value = {
            'tenant_nssai_json': None,
            'tenant_amf_ip': None,
            'tenant_amf_port': None,
            'tenant_plmn': '00101',
            'shared_tac': '1234',
            'duration_mins': 60
        }
        mock_restart.return_value = True
        mock_update_ues.return_value = (False, None, None)
        
        success, error = handle_accepted_state(
            'req-id-123',
            '0xhash123',
            'http://agent:4000'
        )
        
        assert success is True
        assert error is None
        mock_save.assert_called_with('req-id-123', state='Accepted')
    
    @patch('services.state_service.schedule_configuration_restoration')
    @patch('services.state_service.get_and_update_ue_restrictions')
    @patch('services.state_service.restart_agent_with_tenant_config')
    @patch('services.state_service.get_request_data_by_external_requestId')
    @patch('services.state_service.save_request')
    def test_no_duration_specified(self, mock_save, mock_get_data, mock_restart,
                                   mock_update_ues, mock_schedule):
        """Test acceptance without duration (no restoration scheduled)."""
        mock_get_data.return_value = {
            'tenant_nssai_json': None,
            'tenant_amf_ip': None,
            'tenant_amf_port': None,
            'tenant_plmn': '00101',
            'shared_tac': '1234',
            'duration_mins': None
        }
        mock_restart.return_value = True
        mock_update_ues.return_value = (True, [], 0)
        
        success, error = handle_accepted_state(
            'req-id-123',
            '0xhash123',
            'http://agent:4000'
        )
        
        assert success is True
        assert error is None
        mock_schedule.assert_called_once()


class TestUpdateRequestStateHandler:
    """Tests for the main state update handler."""
    
    @patch('services.state_service.get_request_id_by_external_requestId')
    def test_invalid_state(self, mock_get_id):
        """Test handling of invalid state."""
        response, error, status = update_request_state_handler(
            '0xhash123',
            'invalid',
            'http://agent:4000'
        )
        
        assert response is None
        assert 'Invalid state' in error
        assert status == 400
        mock_get_id.assert_not_called()
    
    @patch('services.state_service.get_request_id_by_external_requestId')
    def test_request_not_found(self, mock_get_id):
        """Test handling when request is not found."""
        mock_get_id.return_value = None
        
        response, error, status = update_request_state_handler(
            '0xnonexistent',
            'rejected',
            'http://agent:4000'
        )
        
        assert response is None
        assert 'not found' in error
        assert status == 404
    
    @patch('services.state_service.handle_non_accepted_state')
    @patch('services.state_service.get_request_id_by_external_requestId')
    def test_successful_rejection(self, mock_get_id, mock_handle):
        """Test successful rejection of request."""
        mock_get_id.return_value = 'req-id-123'
        mock_handle.return_value = True
        
        response, error, status = update_request_state_handler(
            '0xhash123',
            'rejected',
            'http://agent:4000'
        )
        
        assert error is None
        assert status == 200
        assert response['success'] is True
        assert response['state'] == 'Rejected'
        assert response['external_requestId'] == '0xhash123'
    
    @patch('services.state_service.handle_accepted_state')
    @patch('services.state_service.get_request_id_by_external_requestId')
    def test_successful_acceptance(self, mock_get_id, mock_handle):
        """Test successful acceptance of request."""
        mock_get_id.return_value = 'req-id-456'
        mock_handle.return_value = (True, None)
        
        response, error, status = update_request_state_handler(
            '0xhash456',
            'accepted',
            'http://agent:4000'
        )
        
        assert error is None
        assert status == 200
        assert response['success'] is True
        assert response['state'] == 'Accepted'
    
    @patch('services.state_service.handle_accepted_state')
    @patch('services.state_service.get_request_id_by_external_requestId')
    def test_acceptance_failure(self, mock_get_id, mock_handle):
        """Test handling of acceptance failure."""
        mock_get_id.return_value = 'req-id-789'
        mock_handle.return_value = (False, "Agent restart failed")
        
        response, error, status = update_request_state_handler(
            '0xhash789',
            'accepted',
            'http://agent:4000'
        )
        
        assert response is None
        assert error == "Agent restart failed"
        assert status == 500
