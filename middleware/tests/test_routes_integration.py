import pytest
import json
import sqlite3
from unittest.mock import patch, MagicMock
from flask import Flask
import database
from main import app as flask_app


@pytest.fixture(autouse=True)
def mock_external_apis():
    """Automatically mock all external API calls for all tests."""
    with patch('routes.requests.post') as mock_node_post, \
         patch('routes.call_agent_restart') as mock_restart, \
         patch('routes.call_agent_get_all_ues') as mock_get_ues, \
         patch('routes.call_agent_update_ues') as mock_update_ues:
        
        # Default mock responses for Node.js server
        mock_node_response = MagicMock()
        mock_node_response.status_code = 200
        mock_node_response.json.return_value = {"txHash": "0xmocked_hash"}
        mock_node_post.return_value = mock_node_response
        
        # Default mock responses for agent calls
        mock_restart_response = MagicMock()
        mock_restart_response.status_code = 200
        mock_restart.return_value = mock_restart_response
        
        mock_ues_response = MagicMock()
        mock_ues_response.status_code = 200
        mock_ues_response.json.return_value = {"ues": []}
        mock_get_ues.return_value = mock_ues_response
        
        mock_update_response = MagicMock()
        mock_update_response.status_code = 200
        mock_update_ues.return_value = mock_update_response
        
        yield {
            'node_post': mock_node_post,
            'agent_restart': mock_restart,
            'agent_get_ues': mock_get_ues,
            'agent_update_ues': mock_update_ues
        }


@pytest.fixture
def app(tmp_path):
    """Create and configure a test Flask app instance."""
    test_db_path = str(tmp_path / 'test_requests.db')
    test_data_dir = str(tmp_path)
    
    with patch('database._DATA_DIR', test_data_dir), \
         patch('database.DB_PATH', test_db_path):
        
        
        database._DATA_DIR = test_data_dir
        database.DB_PATH = test_db_path
        
        # Initialize database with test path
        database.init_db()
        
        # Configure test app
        flask_app.config['TESTING'] = True
        flask_app.config['NODE_SERVER_URL'] = 'http://localhost:3020/api'
        flask_app.config['AGENT_URL'] = 'http://localhost:28080'
        
        yield flask_app


@pytest.fixture
def client(app):
    """Test client for making requests to the API."""
    return app.test_client()


@pytest.fixture
def sample_create_payload():
    """Sample payload for creating a request."""
    return {
        "privateKey": "0xtest123456789",
        "contractAddress": "0xcontract123",
        "sharedTAC": "1234",
        "ueImsis": ["001010000000001", "001010000000002"],
        "durationMins": 60,
        "tenantPLMN": "00101",
        "tenantAMFIP": "192.168.1.1",
        "tenantAMFPort": 38412,
        "tenantNSSAI": [{"sst": 1, "sd": "010203"}]
    }


class TestCreateRequestIntegration:
    """Integration tests for the POST /api/create endpoint."""
    
    def test_create_request_success(self, client, sample_create_payload):
        """Test successful request creation with all fields."""
        with patch('routes.requests.post') as mock_post:
            # Mock successful Node.js response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"txHash": "0xtxhash123"}
            mock_post.return_value = mock_response
            
            response = client.post('/api/create', 
                                  json=sample_create_payload,
                                  content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'txHash' in data
            assert data['txHash'] == '0xtxhash123'
            
            # Verify Node.js was called with correct payload
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]['json']['privateKey'] == sample_create_payload['privateKey']
            assert call_args[1]['json']['numUsers'] == 2
    
    def test_create_request_minimal_payload(self, client):
        """Test request creation with only required fields."""
        minimal_payload = {
            "privateKey": "0xtest123",
            "contractAddress": "0xcontract123",
            "sharedTAC": "5678",
            "ueImsis": ["001010000000003"]
        }
        
        with patch('routes.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"txHash": "0xtxhash456"}
            mock_post.return_value = mock_response
            
            response = client.post('/api/create', 
                                  json=minimal_payload,
                                  content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['txHash'] == '0xtxhash456'
    
    def test_create_request_missing_required_field(self, client):
        """Test that missing required fields return 400 error."""
        incomplete_payload = {
            "privateKey": "0xtest123",
            "contractAddress": "0xcontract123"
            # Missing sharedTAC and ueImsis
        }
        
        response = client.post('/api/create', 
                              json=incomplete_payload,
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Missing' in data['error']
    
    def test_create_request_no_json_data(self, client):
        """Test that request without JSON data returns 400."""
        response = client.post('/api/create', 
                              data='not json',
                              content_type='text/plain')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid JSON format' in data['error']
    
    def test_create_request_node_server_failure(self, client, sample_create_payload):
        """Test handling of Node.js server failures."""
        with patch('routes.requests.post') as mock_post:
            # Mock Node.js server error
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response
            
            response = client.post('/api/create', 
                                  json=sample_create_payload,
                                  content_type='application/json')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            assert 'Failed to process request' in data['error']
    
    def test_create_request_node_server_no_txhash(self, client, sample_create_payload):
        """Test handling when Node.js returns 200 but no txHash."""
        with patch('routes.requests.post') as mock_post:
            # Mock Node.js response without txHash
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": "success"}
            mock_post.return_value = mock_response
            
            response = client.post('/api/create', 
                                  json=sample_create_payload,
                                  content_type='application/json')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            assert 'No transaction hash' in data['error']
    
    def test_create_request_connection_error(self, client, sample_create_payload):
        """Test handling of connection errors to Node.js server."""
        with patch('routes.requests.post') as mock_post:
            import requests as req_module
            mock_post.side_effect = req_module.exceptions.ConnectionError()
            
            response = client.post('/api/create', 
                                  json=sample_create_payload,
                                  content_type='application/json')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            assert 'Failed to forward request' in data['error']
    
    def test_create_request_database_persistence(self, client, sample_create_payload, tmp_path):
        """Test that request data is properly saved to database."""
        with patch('routes.requests.post') as mock_post, \
             patch('database.DB_PATH', str(tmp_path / 'test_requests.db')):
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"txHash": "0xtxhash789"}
            mock_post.return_value = mock_response
            
            response = client.post('/api/create', 
                                  json=sample_create_payload,
                                  content_type='application/json')
            
            assert response.status_code == 200
            
            # Verify data was saved to database
            with sqlite3.connect(str(tmp_path / 'test_requests.db')) as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM requests WHERE tx_hash = ?", ("0xtxhash789",))
                row = c.fetchone()
                assert row is not None


class TestUpdateRequestStateIntegration:
    """Integration tests for the PATCH /api/request/<tx_hash>/<state> endpoint."""
    
    @pytest.fixture
    def existing_request(self, app, tmp_path):
        """Create an existing request in the database."""
        import database
        request_id = "test-uuid-123"
        tx_hash = "0xtesthash"
        
        database.save_request(
            request_id=request_id,
            state='Pending',
            private_key='0xprivate',
            contract_address='0xcontract',
            shared_tac='1234',
            ue_imsis_json='["001010000000001", "001010000000002"]',
            duration_mins=60,
            tenant_plmn='00101',
            tenant_amf_ip='192.168.1.1',
            tenant_amf_port=38412,
            tenant_nssai_json='[{"sst": 1, "sd": "010203"}]',
            tx_hash=tx_hash
        )
        return {"request_id": request_id, "tx_hash": tx_hash}
    
    def test_update_request_to_rejected(self, client, existing_request):
        """Test updating request state to rejected."""
        tx_hash = existing_request['tx_hash']
        
        response = client.patch(f'/api/request/{tx_hash}/rejected')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['state'] == 'Rejected'
        assert data['txHash'] == tx_hash
    
    def test_update_request_to_completed(self, client, existing_request):
        """Test updating request state to completed."""
        tx_hash = existing_request['tx_hash']
        
        response = client.patch(f'/api/request/{tx_hash}/completed')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['state'] == 'Completed'
    
    def test_update_request_to_accepted_agent_success(self, client, existing_request):
        """Test updating request state to accepted with successful agent calls."""
        tx_hash = existing_request['tx_hash']
        
        with patch('routes.call_agent_restart') as mock_restart, \
             patch('routes.call_agent_get_all_ues') as mock_get_ues, \
             patch('routes.call_agent_update_ues') as mock_update_ues:
            
            # Mock successful agent restart
            mock_restart_response = MagicMock()
            mock_restart_response.status_code = 200
            mock_restart.return_value = mock_restart_response
            
            # Mock successful get UEs
            mock_ues_response = MagicMock()
            mock_ues_response.status_code = 200
            mock_ues_response.json.return_value = {
                "ues": [
                    {"imsi": "001010000000001"},
                    {"imsi": "001010000000003"}  # This one should be updated
                ]
            }
            mock_get_ues.return_value = mock_ues_response
            
            # Mock successful update UEs
            mock_update_response = MagicMock()
            mock_update_response.status_code = 200
            mock_update_ues.return_value = mock_update_response
            
            response = client.patch(f'/api/request/{tx_hash}/accepted')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify agent calls were made
            mock_restart.assert_called_once()
            mock_get_ues.assert_called_once()
            mock_update_ues.assert_called_once()
    
    def test_update_request_to_accepted_agent_restart_fails(self, client, existing_request):
        """Test handling of agent restart failure during acceptance."""
        tx_hash = existing_request['tx_hash']
        
        with patch('routes.call_agent_restart') as mock_restart:
            # Mock failed agent restart
            mock_restart_response = MagicMock()
            mock_restart_response.status_code = 500
            mock_restart.return_value = mock_restart_response
            
            response = client.patch(f'/api/request/{tx_hash}/accepted')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            assert 'Failed to restart service' in data['error']
    
    def test_update_request_to_accepted_no_ues_to_update(self, client, existing_request):
        """Test accepting request when all UEs are in the allowed list."""
        tx_hash = existing_request['tx_hash']
        
        with patch('routes.call_agent_restart') as mock_restart, \
             patch('routes.call_agent_get_all_ues') as mock_get_ues:
            
            # Mock successful agent restart
            mock_restart_response = MagicMock()
            mock_restart_response.status_code = 200
            mock_restart.return_value = mock_restart_response
            
            # Mock get UEs - only UEs that are in ue_imsis
            mock_ues_response = MagicMock()
            mock_ues_response.status_code = 200
            mock_ues_response.json.return_value = {
                "ues": [
                    {"imsi": "001010000000001"},
                    {"imsi": "001010000000002"}
                ]
            }
            mock_get_ues.return_value = mock_ues_response
            
            response = client.patch(f'/api/request/{tx_hash}/accepted')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
    
    def test_update_request_invalid_state(self, client, existing_request):
        """Test that invalid state returns 400 error."""
        tx_hash = existing_request['tx_hash']
        
        response = client.patch(f'/api/request/{tx_hash}/invalid_state')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid state' in data['error']
    
    def test_update_request_nonexistent_tx_hash(self, client):
        """Test updating a request with nonexistent tx_hash."""
        response = client.patch('/api/request/0xnonexistent/rejected')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error']
    
    def test_update_request_state_case_insensitive(self, client, existing_request):
        """Test that state parameter is case-insensitive."""
        tx_hash = existing_request['tx_hash']
        
        response = client.patch(f'/api/request/{tx_hash}/REJECTED')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['state'] == 'Rejected'


class TestEndToEndFlow:
    """End-to-end integration tests covering multiple endpoints."""
    
    def test_create_and_update_workflow(self, client, sample_create_payload):
        """Test complete workflow: create request, then update its state."""
        # Step 1: Create request
        with patch('routes.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"txHash": "0xworkflow123"}
            mock_post.return_value = mock_response
            
            create_response = client.post('/api/create', 
                                         json=sample_create_payload,
                                         content_type='application/json')
            
            assert create_response.status_code == 200
            tx_hash = json.loads(create_response.data)['txHash']
        
        # Step 2: Update to rejected
        update_response = client.patch(f'/api/request/{tx_hash}/rejected')
        
        assert update_response.status_code == 200
        data = json.loads(update_response.data)
        assert data['state'] == 'Rejected'
        assert data['txHash'] == tx_hash
    
    def test_create_and_accept_with_full_agent_flow(self, client, sample_create_payload):
        """Test full acceptance workflow with all agent interactions."""
        # Step 1: Create request
        with patch('routes.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"txHash": "0xfullflow123"}
            mock_post.return_value = mock_response
            
            create_response = client.post('/api/create', 
                                         json=sample_create_payload,
                                         content_type='application/json')
            
            assert create_response.status_code == 200
            tx_hash = json.loads(create_response.data)['txHash']
        
        # Step 2: Accept with full agent workflow
        with patch('routes.call_agent_restart') as mock_restart, \
             patch('routes.call_agent_get_all_ues') as mock_get_ues, \
             patch('routes.call_agent_update_ues') as mock_update_ues:
            
            # Mock all agent calls
            mock_restart_response = MagicMock()
            mock_restart_response.status_code = 200
            mock_restart.return_value = mock_restart_response
            
            mock_ues_response = MagicMock()
            mock_ues_response.status_code = 200
            mock_ues_response.json.return_value = {
                "ues": [
                    {"imsi": "001010000000001"},
                    {"imsi": "001010000000003"}
                ]
            }
            mock_get_ues.return_value = mock_ues_response
            
            mock_update_response = MagicMock()
            mock_update_response.status_code = 200
            mock_update_ues.return_value = mock_update_response
            
            accept_response = client.patch(f'/api/request/{tx_hash}/accepted')
            
            assert accept_response.status_code == 200
            data = json.loads(accept_response.data)
            assert data['success'] is True
            
            # Verify the agent call flow
            assert mock_restart.call_count == 1
            assert mock_get_ues.call_count == 1
            assert mock_update_ues.call_count == 1
