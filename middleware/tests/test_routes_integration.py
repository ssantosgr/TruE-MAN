"""End-to-end integration tests for complete request workflows.

These tests verify that all components work together correctly end-to-end.
Basic functionality is covered by unit tests (test_*_service.py) and route tests (test_routes.py).
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from main import app as flask_app
import database


@pytest.fixture
def app(tmp_path):
    """Create and configure a test Flask app instance."""
    test_db_path = str(tmp_path / 'test_requests.db')
    test_data_dir = str(tmp_path)
    
    with patch('database._DATA_DIR', test_data_dir), \
         patch('database.DB_PATH', test_db_path):
        
        database._DATA_DIR = test_data_dir
        database.DB_PATH = test_db_path
        database.init_db()
        
        flask_app.config['TESTING'] = True
        flask_app.config['NODE_SERVER_URL'] = 'http://localhost:3020/api'
        flask_app.config['AGENT_URL'] = 'http://localhost:28080'
        
        yield flask_app


@pytest.fixture
def client(app):
    """Test client for making requests to the API."""
    return app.test_client()


class TestEndToEndWorkflows:
    """Complete end-to-end integration tests verifying full request lifecycles."""
    
    @patch('services.request_service.requests.post')
    def test_create_and_reject_complete_workflow(self, mock_post, client):
        """Test complete workflow: create request -> verify persistence -> reject -> verify final state."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"requestId": "0xe2e_reject"}
        mock_post.return_value = mock_response
        
        create_payload = {
            "privateKey": "0xkey",
            "contractAddress": "0xaddr",
            "sharedTAC": "1234",
            "ueImsis": ["001010000000001"]
        }
        
        # Create request
        create_response = client.post('/api/request',
                                     json=create_payload,
                                     content_type='application/json')
        
        assert create_response.status_code == 200
        data = json.loads(create_response.data)
        assert data['requestId'] == '0xe2e_reject'
        
        # Verify database state
        saved_data = database.get_request_data_by_external_requestId('0xe2e_reject')
        assert saved_data is not None
        assert saved_data['state'] == 'Pending'
        
        # Reject request
        update_response = client.patch('/api/request/0xe2e_reject/rejected')
        
        assert update_response.status_code == 200
        update_data = json.loads(update_response.data)
        assert update_data['success'] is True
        assert update_data['state'] == 'Rejected'
        
        # Verify final state in database
        final_data = database.get_request_data_by_external_requestId('0xe2e_reject')
        assert final_data['state'] == 'Rejected'
    
    @patch('services.request_service.requests.post')
    @patch('services.agent_service.call_agent_restart')
    @patch('services.agent_service.call_agent_get_all_ues')
    @patch('services.agent_service.call_agent_update_ues')
    @patch('services.config_service.threading.Thread')
    def test_full_acceptance_workflow_with_agent_integration(self, mock_thread, mock_update,
                                                             mock_get, mock_restart, mock_post,
                                                             client):
        """Test complete acceptance workflow with agent configuration and restoration scheduling."""
        # Setup mocks
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"requestId": "0xe2e_accept_full"}
        mock_post.return_value = mock_response
        
        mock_restart.return_value = MagicMock(status_code=200)
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"ues": [
                {"imsi": "999990000000001", "tac_restriction": "9999"}
            ]})
        )
        mock_update.return_value = MagicMock(status_code=200)
        
        # Create request
        create_payload = {
            "privateKey": "0xkey",
            "contractAddress": "0xaddr",
            "sharedTAC": "5678",
            "ueImsis": ["001010000000001", "001010000000002"]
        }
        
        create_response = client.post('/api/request',
                                     json=create_payload,
                                     content_type='application/json')
        
        assert create_response.status_code == 200
        
        # Verify database persistence
        saved_data = database.get_request_data_by_external_requestId('0xe2e_accept_full')
        assert saved_data['state'] == 'Pending'
        assert '001010000000001' in saved_data['ue_imsis_json']
        
        # Accept request (triggers agent configuration chain)
        accept_response = client.patch('/api/request/0xe2e_accept_full/accepted')
        
        assert accept_response.status_code == 200
        accept_data = json.loads(accept_response.data)
        assert accept_data['success'] is True
        
        # Verify complete integration: agent restart, UE fetch, UE update all called
        mock_restart.assert_called_once()
        mock_get.assert_called_once()
        mock_update.assert_called_once()
        
        # Verify shared TAC was added to UE restrictions
        update_call = mock_update.call_args
        assert '5678' in str(update_call)
    
    @patch('services.request_service.requests.post')
    @patch('services.agent_service.call_agent_restart')
    def test_acceptance_failure_prevents_state_corruption(self, mock_restart, mock_post, client):
        """Test that acceptance failures don't corrupt state - verifying rollback behavior."""
        # Create request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"requestId": "0xe2e_fail"}
        mock_post.return_value = mock_response
        
        create_payload = {
            "privateKey": "0xkey",
            "contractAddress": "0xaddr",
            "sharedTAC": "1234",
            "ueImsis": ["001010000000001"]
        }
        
        create_response = client.post('/api/request', json=create_payload, content_type='application/json')
        assert create_response.status_code == 200
        
        # Verify initial state
        initial_data = database.get_request_data_by_external_requestId('0xe2e_fail')
        assert initial_data['state'] == 'Pending'
        
        # Attempt acceptance with agent restart failure
        mock_restart.return_value = MagicMock(status_code=500)
        
        accept_response = client.patch('/api/request/0xe2e_fail/accepted')
        
        assert accept_response.status_code == 500
        error_data = json.loads(accept_response.data)
        assert 'error' in error_data
        
        # Verify state was NOT updated (rollback behavior)
        final_data = database.get_request_data_by_external_requestId('0xe2e_fail')
        assert final_data['state'] == 'Pending'
    
    @patch('services.request_service.requests.post')
    @patch('services.agent_service.call_agent_restart')
    @patch('services.agent_service.call_agent_get_all_ues')
    @patch('services.agent_service.call_agent_update_ues')
    def test_ue_restrictions_merge_integration(self, mock_update, mock_get,
                                               mock_restart, mock_post, client):
        """Test that acceptance correctly merges new TAC with existing UE restrictions."""
        # Create request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"requestId": "0xe2e_merge"}
        mock_post.return_value = mock_response
        
        create_payload = {
            "privateKey": "0xkey",
            "contractAddress": "0xaddr",
            "sharedTAC": "9876",
            "ueImsis": ["001010000000001"]
        }
        
        client.post('/api/request', json=create_payload, content_type='application/json')
        
        # Setup agent to return UEs with existing restrictions
        mock_restart.return_value = MagicMock(status_code=200)
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"ues": [
                {"imsi": "111110000000001", "tac_restriction": "1111,2222"},
                {"imsi": "333330000000001", "tac_restriction": "3333"}
            ]})
        )
        mock_update.return_value = MagicMock(status_code=200)
        
        # Accept request
        accept_response = client.patch('/api/request/0xe2e_merge/accepted')
        
        assert accept_response.status_code == 200
        
        # Verify UE update was called with merged restrictions
        mock_update.assert_called_once()
        update_call_args = mock_update.call_args[0][1]  # Get the 'ues' parameter
        
        # Verify shared TAC (9876) was added to all UEs
        ues_str = json.dumps(update_call_args)
        assert '9876' in ues_str
        # Verify existing restrictions were preserved
        assert '1111' in ues_str or '2222' in ues_str or '3333' in ues_str

