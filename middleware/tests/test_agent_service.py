"""Unit tests for agent_service module."""
import pytest
import json
from unittest.mock import patch, MagicMock
from services.agent_service import (
    restart_agent_with_tenant_config,
    get_and_update_ue_restrictions
)


class TestRestartAgentWithTenantConfig:
    """Tests for agent restart with tenant configuration."""
    
    @patch('services.agent_service.call_agent_restart')
    def test_restart_with_full_config(self, mock_restart):
        """Test agent restart with complete tenant configuration."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_restart.return_value = mock_response
        
        request_data = {
            'tenant_nssai_json': '[{"sst": 1, "sd": "010203"}]',
            'tenant_amf_ip': '192.168.1.1',
            'tenant_amf_port': 38412,
            'tenant_plmn': '00101',
            'shared_tac': '1234'
        }
        
        result = restart_agent_with_tenant_config('http://agent:4000', request_data)
        
        assert result is True
        mock_restart.assert_called_once()
        call_args = mock_restart.call_args[1]
        assert call_args['amf_addr_tenant'] == '192.168.1.1:38412'
        assert call_args['nssai_tenant'] == [{"sst": 1, "sd": "010203"}]
        assert call_args['plmn_tenant'] == '00101'
        assert call_args['tac_tenant'] == 1234
    
    @patch('services.agent_service.call_agent_restart')
    def test_restart_with_ip_only(self, mock_restart):
        """Test agent restart with IP but no port."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_restart.return_value = mock_response
        
        request_data = {
            'tenant_nssai_json': None,
            'tenant_amf_ip': '192.168.1.1',
            'tenant_amf_port': None,
            'tenant_plmn': '00101',
            'shared_tac': '5678'
        }
        
        result = restart_agent_with_tenant_config('http://agent:4000', request_data)
        
        assert result is True
        call_args = mock_restart.call_args[1]
        assert call_args['amf_addr_tenant'] == '192.168.1.1'
    
    @patch('services.agent_service.call_agent_restart')
    def test_restart_failure(self, mock_restart):
        """Test handling of agent restart failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_restart.return_value = mock_response
        
        request_data = {
            'tenant_nssai_json': None,
            'tenant_amf_ip': None,
            'tenant_amf_port': None,
            'tenant_plmn': '00101',
            'shared_tac': '1234'
        }
        
        result = restart_agent_with_tenant_config('http://agent:4000', request_data)
        
        assert result is False
    
    @patch('services.agent_service.call_agent_restart')
    def test_restart_with_minimal_config(self, mock_restart):
        """Test agent restart with minimal configuration."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_restart.return_value = mock_response
        
        request_data = {
            'tenant_nssai_json': None,
            'tenant_amf_ip': None,
            'tenant_amf_port': None,
            'tenant_plmn': None,
            'shared_tac': None
        }
        
        result = restart_agent_with_tenant_config('http://agent:4000', request_data)
        
        assert result is True
        call_args = mock_restart.call_args[1]
        assert call_args['amf_addr_tenant'] is None
        assert call_args['nssai_tenant'] is None


class TestGetAndUpdateUeRestrictions:
    """Tests for getting and updating UE restrictions."""
    
    @patch('services.agent_service.call_agent_update_ues')
    @patch('services.agent_service.call_agent_get_all_ues')
    def test_successful_ue_update(self, mock_get_ues, mock_update_ues):
        """Test successful UE restriction update."""
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "ues": [
                {"imsi": "001010000000001"},
                {"imsi": "001010000000002"},
                {"imsi": "001010000000003"}
            ]
        }
        mock_get_ues.return_value = mock_get_response
        
        mock_update_response = MagicMock()
        mock_update_response.status_code = 200
        mock_update_ues.return_value = mock_update_response
        
        request_data = {
            'ue_imsis_json': '["001010000000001"]',
            'shared_tac': '1234',
            'tenant_plmn': '00101'
        }
        
        success, original_ues, num_updated = get_and_update_ue_restrictions(
            'http://agent:4000',
            request_data
        )
        
        assert success is True
        assert len(original_ues) == 2  # Only UEs not in ue_imsis
        assert num_updated == 2
        mock_update_ues.assert_called_once()
    
    @patch('services.agent_service.call_agent_get_all_ues')
    def test_get_ues_failure(self, mock_get_ues):
        """Test handling of get UEs failure."""
        mock_get_response = MagicMock()
        mock_get_response.status_code = 500
        mock_get_ues.return_value = mock_get_response
        
        request_data = {
            'ue_imsis_json': '["001010000000001"]',
            'shared_tac': '1234',
            'tenant_plmn': '00101'
        }
        
        success, original_ues, num_updated = get_and_update_ue_restrictions(
            'http://agent:4000',
            request_data
        )
        
        assert success is False
        assert original_ues is None
        assert num_updated is None
    
    @patch('services.agent_service.call_agent_update_ues')
    @patch('services.agent_service.call_agent_get_all_ues')
    def test_update_ues_failure(self, mock_get_ues, mock_update_ues):
        """Test handling of update UEs failure."""
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "ues": [
                {"imsi": "001010000000001"},
                {"imsi": "001010000000002"}
            ]
        }
        mock_get_ues.return_value = mock_get_response
        
        mock_update_response = MagicMock()
        mock_update_response.status_code = 500
        mock_update_ues.return_value = mock_update_response
        
        request_data = {
            'ue_imsis_json': '["001010000000001"]',
            'shared_tac': '1234',
            'tenant_plmn': '00101'
        }
        
        success, original_ues, num_updated = get_and_update_ue_restrictions(
            'http://agent:4000',
            request_data
        )
        
        assert success is False
        assert original_ues is None
        assert num_updated is None
    
    @patch('services.agent_service.call_agent_update_ues')
    @patch('services.agent_service.call_agent_get_all_ues')
    def test_no_ues_to_update(self, mock_get_ues, mock_update_ues):
        """Test when all UEs are in the allowed list."""
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "ues": [
                {"imsi": "001010000000001"},
                {"imsi": "001010000000002"}
            ]
        }
        mock_get_ues.return_value = mock_get_response
        
        request_data = {
            'ue_imsis_json': '["001010000000001", "001010000000002"]',
            'shared_tac': '1234',
            'tenant_plmn': '00101'
        }
        
        success, original_ues, num_updated = get_and_update_ue_restrictions(
            'http://agent:4000',
            request_data
        )
        
        assert success is True
        assert len(original_ues) == 0
        assert num_updated == 0
        mock_update_ues.assert_not_called()
    
    @patch('services.agent_service.call_agent_get_all_ues')
    def test_invalid_json_in_ue_imsis(self, mock_get_ues):
        """Test handling of invalid JSON in ue_imsis."""
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"ues": [{"imsi": "001010000000001"}]}
        mock_get_ues.return_value = mock_get_response
        
        request_data = {
            'ue_imsis_json': 'invalid json',
            'shared_tac': '1234',
            'tenant_plmn': '00101'
        }
        
        success, original_ues, num_updated = get_and_update_ue_restrictions(
            'http://agent:4000',
            request_data
        )
        
        assert success is False
        assert original_ues is None
        assert num_updated is None
    
    @patch('services.agent_service.call_agent_update_ues')
    @patch('services.agent_service.call_agent_get_all_ues')
    def test_tac_restriction_added_correctly(self, mock_get_ues, mock_update_ues):
        """Test that TAC restrictions are added to UE configuration."""
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "ues": [
                {"imsi": "001010000000002"}
            ]
        }
        mock_get_ues.return_value = mock_get_response
        
        mock_update_response = MagicMock()
        mock_update_response.status_code = 200
        mock_update_ues.return_value = mock_update_response
        
        request_data = {
            'ue_imsis_json': '["001010000000001"]',
            'shared_tac': '1234',
            'tenant_plmn': '00101'
        }
        
        success, original_ues, num_updated = get_and_update_ue_restrictions(
            'http://agent:4000',
            request_data
        )
        
        assert success is True
        # Verify the UE was modified
        call_args = mock_update_ues.call_args[0]
        updated_ues = call_args[1]
        assert len(updated_ues) == 1
        assert 'allowed_5gs_tais' in updated_ues[0]
        assert updated_ues[0]['allowed_5gs_tais']['restriction_type'] == 'not_allowed'
