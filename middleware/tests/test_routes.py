"""Integration tests for API routes."""
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


class TestCreateRequestRoute:
    """Integration tests for POST /api/request route."""
    
    @patch('services.request_service.requests.post')
    def test_successful_request_creation(self, mock_post, client):
        """Test successful request creation through the route."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"requestId": "0xhash123"}
        mock_post.return_value = mock_response
        
        payload = {
            "privateKey": "0xtest",
            "contractAddress": "0xcontract",
            "sharedTAC": "1234",
            "ueImsis": ["001010000000001"]
        }
        
        response = client.post('/api/request',
                              json=payload,
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['requestId'] == '0xhash123'
    
    def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        response = client.post('/api/request',
                              data='not json',
                              content_type='text/plain')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid JSON' in data['error']
    
    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        payload = {
            "privateKey": "0xtest"
            # Missing other required fields
        }
        
        response = client.post('/api/request',
                              json=payload,
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestUpdateRequestStateRoute:
    """Integration tests for PATCH /api/request/<external_requestId>/<state> route."""
    
    @pytest.fixture
    def existing_request(self, app):
        """Create an existing request in the database."""
        request_id = "test-uuid-123"
        external_requestId = "0xtesthash"
        
        database.save_request(
            request_id=request_id,
            state='Pending',
            private_key='0xprivate',
            contract_address='0xcontract',
            shared_tac='1234',
            ue_imsis_json='["001010000000001"]',
            external_requestId=external_requestId
        )
        return {"request_id": request_id, "external_requestId": external_requestId}
    
    def test_successful_rejection(self, client, existing_request):
        """Test successful rejection of request."""
        external_requestId = existing_request['external_requestId']
        
        response = client.patch(f'/api/request/{external_requestId}/rejected')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['state'] == 'Rejected'
    
    def test_invalid_state(self, client, existing_request):
        """Test handling of invalid state."""
        external_requestId = existing_request['external_requestId']
        
        response = client.patch(f'/api/request/{external_requestId}/invalid')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_nonexistent_request(self, client):
        """Test handling of nonexistent request."""
        response = client.patch('/api/request/0xnonexistent/rejected')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('services.agent_service.call_agent_restart')
    @patch('services.agent_service.call_agent_get_all_ues')
    @patch('services.agent_service.call_agent_update_ues')
    def test_successful_acceptance(self, mock_update, mock_get, mock_restart,
                                   client, existing_request):
        """Test successful acceptance of request."""
        mock_restart.return_value = MagicMock(status_code=200)
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"ues": []})
        )
        mock_update.return_value = MagicMock(status_code=200)
        
        external_requestId = existing_request['external_requestId']
        
        response = client.patch(f'/api/request/{external_requestId}/accepted')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True


class TestRouteErrorHandling:
    """Tests for route-level error handling."""
    
    @patch('services.request_service.create_request_handler')
    def test_unexpected_error_in_create(self, mock_handler, client):
        """Test handling of unexpected errors in create route."""
        mock_handler.side_effect = Exception("Unexpected error")
        
        payload = {
            "privateKey": "0xtest",
            "contractAddress": "0xcontract",
            "sharedTAC": "1234",
            "ueImsis": ["001010000000001"]
        }
        
        response = client.post('/api/request',
                              json=payload,
                              content_type='application/json')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('routes.update_request_state_handler')
    def test_unexpected_error_in_update(self, mock_handler, client):
        """Test handling of unexpected errors in update route."""
        mock_handler.side_effect = Exception("Unexpected error")
        
        response = client.patch('/api/request/0xhash/rejected')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
