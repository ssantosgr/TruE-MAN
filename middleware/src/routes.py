"""API routes for the middleware service."""
from flask import Blueprint, request, jsonify, current_app
import logging
from services.request_service import create_request_handler
from services.state_service import update_request_state_handler

api = Blueprint('api', __name__)


@api.route('/api/request', methods=['POST'])
def create_request():
    """Create a new request and forward to blockchain server."""
    try:
        # Parse JSON payload
        try:
            data = request.get_json()
        except Exception as e:
            logging.error(f"Failed to parse JSON: {e}")
            return jsonify({"error": "Invalid JSON format"}), 400
        
        # Get Node.js server URL from config
        node_server_url = current_app.config.get('NODE_SERVER_URL', "http://localhost:3020/api")
        
        # Call service handler
        response_data, error_msg, status_code = create_request_handler(data, node_server_url)
        
        if error_msg:
            return jsonify({"error": error_msg}), status_code
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500


@api.route('/api/request/<external_requestId>/<state>', methods=['PATCH'])
def update_request_state(external_requestId, state):
    """Update request state (accepted/rejected/completed)."""
    try:
        # Get agent URL from config
        agent_url = current_app.config.get('AGENT_URL', 'http://localhost:4000/resource/1')
        
        # Call service handler
        response_data, error_msg, status_code = update_request_state_handler(
            external_requestId, 
            state, 
            agent_url
        )
        
        if error_msg:
            return jsonify({"error": error_msg}), status_code
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        logging.error(f"Unexpected error in update_request_state: {e}")
        return jsonify({"error": str(e)}), 500
