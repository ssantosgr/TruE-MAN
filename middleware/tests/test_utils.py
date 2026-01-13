import pytest
from unittest.mock import patch, MagicMock
import json

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils import (
    call_agent,
    call_agent_restart,
    call_agent_get_all_ues,
    call_agent_update_ues,
    _build_payload,
    _create_error_response,
    DEFAULT_GNB_ID,
    RESTART_PARAM_MAPPING,
)


class TestBuildPayload:
    def test_payload_without_parameters(self):
        """Test building payload without action parameters."""
        payload = _build_payload('test_action')
        
        assert payload == {
            "activation_feature": [{
                "name": "gNodeB_service",
                "feature_characteristic": [
                    {"name": "action", "value": {"value": "test_action"}}
                ]
            }]
        }
    
    def test_payload_with_parameters(self):
        """Test building payload with action parameters."""
        params = {"key": "value"}
        payload = _build_payload('test_action', params)
        
        characteristics = payload["activation_feature"][0]["feature_characteristic"]
        assert len(characteristics) == 2
        assert characteristics[1] == {
            "name": "action_parameters",
            "value": {"value": {"key": "value"}}
        }
    
    def test_payload_with_list_parameters(self):
        """Test building payload with list as action parameters."""
        params = [{"ue": "data"}]
        payload = _build_payload('update_ues', params)
        
        characteristics = payload["activation_feature"][0]["feature_characteristic"]
        assert characteristics[1]["value"]["value"] == [{"ue": "data"}]


class TestCreateErrorResponse:
    def test_default_error_response(self):
        """Test creating default error response."""
        response = _create_error_response()
        
        assert response.status_code == 500
        assert response.content == b"Internal Server Error"
    
    def test_custom_error_response(self):
        """Test creating custom error response."""
        response = _create_error_response(404, "Not Found")
        
        assert response.status_code == 404
        assert response.content == b"Not Found"


class TestCallAgent:
    @patch('utils.requests.patch')
    def test_successful_call(self, mock_patch):
        """Test successful agent call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_patch.return_value = mock_response
        
        result = call_agent('test_action', 'http://localhost:4000')
        
        mock_patch.assert_called_once()
        call_args = mock_patch.call_args
        assert f'/resource/{DEFAULT_GNB_ID}' in call_args[0][0]
        assert result.status_code == 200
    
    @patch('utils.requests.patch')
    def test_url_formatting(self, mock_patch):
        """Test that URL is correctly formatted."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response
        
        # Test with trailing slash
        call_agent('test', 'http://localhost:4000/')
        url = mock_patch.call_args[0][0]
        assert url == f'http://localhost:4000/resource/{DEFAULT_GNB_ID}'
        
        # Test without trailing slash
        call_agent('test', 'http://localhost:4000')
        url = mock_patch.call_args[0][0]
        assert url == f'http://localhost:4000/resource/{DEFAULT_GNB_ID}'
    
    @patch('utils.requests.patch')
    def test_request_exception_returns_error_response(self, mock_patch):
        """Test that request exceptions return error response."""
        import requests
        mock_patch.side_effect = requests.exceptions.RequestException("Connection failed")
        
        result = call_agent('test_action', 'http://localhost:4000')
        
        assert result.status_code == 500
        assert result.content == b"Internal Server Error"
    
    @patch('utils.requests.patch')
    def test_payload_sent_as_json(self, mock_patch):
        """Test that payload is sent as JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response
        
        call_agent('test_action', 'http://localhost:4000', {"param": "value"})
        
        call_kwargs = mock_patch.call_args[1]
        assert call_kwargs['headers'] == {"Content-Type": "application/json"}
        
        sent_data = json.loads(call_kwargs['data'])
        assert sent_data['activation_feature'][0]['name'] == 'gNodeB_service'


class TestCallAgentRestart:
    @patch('utils.call_agent')
    def test_restart_with_all_params(self, mock_call_agent):
        """Test restart with all tenant parameters."""
        mock_call_agent.return_value = MagicMock(status_code=200)
        
        call_agent_restart(
            'http://localhost:4000',
            amf_addr_tenant='192.168.1.1:38412',
            nssai_tenant=[{"sst": 1}],
            plmn_tenant='00101',
            tac_tenant=101
        )
        
        mock_call_agent.assert_called_once()
        call_args = mock_call_agent.call_args
        
        assert call_args[0][0] == 'restart'
        assert call_args[0][1] == 'http://localhost:4000'
        
        params = call_args[0][2]
        assert params['PRMT_AMF_ADDR_TENANT'] == '192.168.1.1:38412'
        assert params['PRMT_NSSAI_TENANT'] == [{"sst": 1}]
        assert params['PRMT_PLMN_TENANT'] == '00101'
        assert params['PRMT_TAC_TENANT'] == 101
    
    @patch('utils.call_agent')
    def test_restart_with_partial_params(self, mock_call_agent):
        """Test restart with only some parameters."""
        mock_call_agent.return_value = MagicMock(status_code=200)
        
        call_agent_restart(
            'http://localhost:4000',
            plmn_tenant='00101'
        )
        
        params = mock_call_agent.call_args[0][2]
        assert params == {'PRMT_PLMN_TENANT': '00101'}
    
    @patch('utils.call_agent')
    def test_restart_with_no_params(self, mock_call_agent):
        """Test restart with no parameters."""
        mock_call_agent.return_value = MagicMock(status_code=200)
        
        call_agent_restart('http://localhost:4000')
        
        params = mock_call_agent.call_args[0][2]
        assert params is None
    
    @patch('utils.call_agent')
    def test_restart_ignores_none_values(self, mock_call_agent):
        """Test that None values are ignored."""
        mock_call_agent.return_value = MagicMock(status_code=200)
        
        call_agent_restart(
            'http://localhost:4000',
            amf_addr_tenant=None,
            plmn_tenant='00101',
            tac_tenant=None
        )
        
        params = mock_call_agent.call_args[0][2]
        assert params == {'PRMT_PLMN_TENANT': '00101'}


class TestCallAgentGetAllUes:
    @patch('utils.call_agent')
    def test_get_all_ues(self, mock_call_agent):
        """Test getting all UEs."""
        mock_call_agent.return_value = MagicMock(status_code=200)
        
        call_agent_get_all_ues('http://localhost:4000')
        
        mock_call_agent.assert_called_once_with('get_all_ues', 'http://localhost:4000')


class TestCallAgentUpdateUes:
    @patch('utils.call_agent')
    def test_update_ues(self, mock_call_agent):
        """Test updating UEs."""
        mock_call_agent.return_value = MagicMock(status_code=200)
        
        ues = [
            {
                "sim_algo": "milenage",
                "imsi": "001010000045613",
                "opc": "C04126AC784BC27D1E24DEFDF4B1CD44",
                "amf": "0x9001",
                "sqn": "000000000000",
                "K": "F6D8D81A6523107FB2473983739221A0",
                "pdn_list": [{"access_point_name": "internet", "nssai": [{"sst": 1}]}],
                "impi": "001010000045613@ims.mnc001.mcc001.3gppnetwork.org",
                "impu": ["001010000045613"],
                "allowed_5gs_tais": {
                    "restriction_type": "not_allowed",
                    "tais": [{"plmn": "00101", "areas": [{"tacs": [101]}]}]
                }
            }
        ]
        
        call_agent_update_ues('http://localhost:4000', ues)
        
        mock_call_agent.assert_called_once_with('update_ues', 'http://localhost:4000', ues)
    
    @patch('utils.call_agent')
    def test_update_empty_ues_list(self, mock_call_agent):
        """Test updating with empty UEs list."""
        mock_call_agent.return_value = MagicMock(status_code=200)
        
        call_agent_update_ues('http://localhost:4000', [])
        
        mock_call_agent.assert_called_once_with('update_ues', 'http://localhost:4000', [])
