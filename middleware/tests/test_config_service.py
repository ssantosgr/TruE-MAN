"""Unit tests for config_service module."""
import pytest
from unittest.mock import patch, MagicMock, call
from services.config_service import (
    restore_configuration,
    schedule_configuration_restoration
)


class TestRestoreConfiguration:
    """Tests for configuration restoration."""
    
    @patch('services.config_service.time.sleep')
    @patch('services.config_service.save_request')
    @patch('services.config_service.call_agent_update_ues')
    @patch('services.config_service.call_agent_restart')
    def test_successful_restoration(self, mock_restart, mock_update, mock_save, mock_sleep):
        """Test successful configuration restoration."""
        mock_restart.return_value = MagicMock(status_code=200)
        mock_update.return_value = MagicMock(status_code=200)
        
        original_ues = [
            {"imsi": "001010000000001", "allowed_5gs_tais": {"restriction_type": "allowed"}},
            {"imsi": "001010000000002"}
        ]
        
        restore_configuration(
            'req-id-123',
            '0xhash123',
            'http://agent:4000',
            original_ues,
            1  # 1 minute for testing
        )
        
        # Verify sleep was called with correct duration
        mock_sleep.assert_called_once_with(60)  # 1 minute * 60 seconds
        
        # Verify agent restart was called with null values
        mock_restart.assert_called_once()
        call_kwargs = mock_restart.call_args[1]
        assert call_kwargs['amf_addr_tenant'] is None
        assert call_kwargs['nssai_tenant'] is None
        assert call_kwargs['plmn_tenant'] is None
        assert call_kwargs['tac_tenant'] is None
        
        # Verify UEs were restored
        mock_update.assert_called_once_with('http://agent:4000', original_ues)
        
        # Verify state was updated to Expired
        mock_save.assert_called_with('req-id-123', state='Expired')
    
    @patch('services.config_service.time.sleep')
    @patch('services.config_service.save_request')
    @patch('services.config_service.call_agent_restart')
    def test_agent_restart_failure(self, mock_restart, mock_save, mock_sleep):
        """Test handling of agent restart failure during restoration."""
        mock_restart.return_value = MagicMock(status_code=500)
        
        original_ues = [{"imsi": "001010000000001"}]
        
        restore_configuration(
            'req-id-456',
            '0xhash456',
            'http://agent:4000',
            original_ues,
            1
        )
        
        # Verify state was updated to RestoreFailed
        mock_save.assert_called_with('req-id-456', state='RestoreFailed')
    
    @patch('services.config_service.time.sleep')
    @patch('services.config_service.save_request')
    @patch('services.config_service.call_agent_update_ues')
    @patch('services.config_service.call_agent_restart')
    def test_ue_update_failure(self, mock_restart, mock_update, mock_save, mock_sleep):
        """Test handling of UE update failure during restoration."""
        mock_restart.return_value = MagicMock(status_code=200)
        mock_update.return_value = MagicMock(status_code=500)
        
        original_ues = [{"imsi": "001010000000001"}]
        
        restore_configuration(
            'req-id-789',
            '0xhash789',
            'http://agent:4000',
            original_ues,
            1
        )
        
        # Verify state was updated to RestoreFailed
        mock_save.assert_called_with('req-id-789', state='RestoreFailed')
    
    @patch('services.config_service.time.sleep')
    @patch('services.config_service.save_request')
    @patch('services.config_service.call_agent_restart')
    def test_no_ues_to_restore(self, mock_restart, mock_save, mock_sleep):
        """Test restoration when there are no UEs to restore."""
        mock_restart.return_value = MagicMock(status_code=200)
        
        restore_configuration(
            'req-id-321',
            '0xhash321',
            'http://agent:4000',
            [],  # Empty UE list
            1
        )
        
        # Verify state was still updated to Expired
        mock_save.assert_called_with('req-id-321', state='Expired')
    
    @patch('services.config_service.time.sleep')
    @patch('services.config_service.save_request')
    @patch('services.config_service.call_agent_restart')
    def test_exception_during_restoration(self, mock_restart, mock_save, mock_sleep):
        """Test handling of unexpected exceptions during restoration."""
        mock_restart.side_effect = Exception("Network error")
        
        original_ues = [{"imsi": "001010000000001"}]
        
        restore_configuration(
            'req-id-999',
            '0xhash999',
            'http://agent:4000',
            original_ues,
            1
        )
        
        # Verify state was updated to RestoreFailed
        mock_save.assert_called_with('req-id-999', state='RestoreFailed')
    
    @patch('services.config_service.time.sleep')
    @patch('services.config_service.save_request')
    @patch('services.config_service.call_agent_update_ues')
    @patch('services.config_service.call_agent_restart')
    def test_duration_calculation(self, mock_restart, mock_update, mock_save, mock_sleep):
        """Test that duration is correctly converted to seconds."""
        mock_restart.return_value = MagicMock(status_code=200)
        mock_update.return_value = MagicMock(status_code=200)
        
        restore_configuration(
            'req-id-111',
            '0xhash111',
            'http://agent:4000',
            [],
            30  # 30 minutes
        )
        
        # Verify sleep was called with 30 minutes * 60 seconds
        mock_sleep.assert_called_once_with(1800)


class TestScheduleConfigurationRestoration:
    """Tests for scheduling configuration restoration."""
    
    @patch('services.config_service.threading.Thread')
    def test_schedules_with_valid_duration(self, mock_thread):
        """Test that restoration is scheduled when duration is valid."""
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        original_ues = [{"imsi": "001010000000001"}]
        
        schedule_configuration_restoration(
            'req-id-123',
            '0xhash123',
            'http://agent:4000',
            original_ues,
            60
        )
        
        # Verify thread was created
        mock_thread.assert_called_once()
        call_kwargs = mock_thread.call_args[1]
        assert call_kwargs['daemon'] is True
        assert len(call_kwargs['args']) == 5
        
        # Verify thread was started
        mock_thread_instance.start.assert_called_once()
    
    @patch('services.config_service.threading.Thread')
    def test_does_not_schedule_with_zero_duration(self, mock_thread):
        """Test that restoration is not scheduled when duration is zero."""
        schedule_configuration_restoration(
            'req-id-456',
            '0xhash456',
            'http://agent:4000',
            [],
            0
        )
        
        # Verify thread was not created
        mock_thread.assert_not_called()
    
    @patch('services.config_service.threading.Thread')
    def test_does_not_schedule_with_none_duration(self, mock_thread):
        """Test that restoration is not scheduled when duration is None."""
        schedule_configuration_restoration(
            'req-id-789',
            '0xhash789',
            'http://agent:4000',
            [],
            None
        )
        
        # Verify thread was not created
        mock_thread.assert_not_called()
    
    @patch('services.config_service.threading.Thread')
    def test_does_not_schedule_with_negative_duration(self, mock_thread):
        """Test that restoration is not scheduled when duration is negative."""
        schedule_configuration_restoration(
            'req-id-321',
            '0xhash321',
            'http://agent:4000',
            [],
            -10
        )
        
        # Verify thread was not created
        mock_thread.assert_not_called()
