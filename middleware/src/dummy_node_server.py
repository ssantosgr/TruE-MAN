"""Dummy Node.js server for testing purposes.

This server mocks the blockchain Node.js server API endpoints.
Run with: python dummy_node_server.py
"""
from flask import Flask, request, jsonify
import logging
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# In-memory storage for requests
requests_store = {}


@app.route('/api/create', methods=['POST'])
def create_request():
    """Mock endpoint for creating blockchain requests."""
    try:
        data = request.get_json()
        logging.info(f"Received create request: {data}")
        
        # Validate required fields
        required = ['privateKey', 'contractAddress', 'numUsers', 'durationMins']
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing)}"
            }), 400
        
        # Generate a mock request ID (simulating blockchain transaction)
        request_id = f"0x{uuid.uuid4().hex}"
        
        # Store the request
        requests_store[request_id] = {
            "requestId": request_id,
            "privateKey": data.get('privateKey'),
            "contractAddress": data.get('contractAddress'),
            "numUsers": data.get('numUsers'),
            "durationMins": data.get('durationMins'),
            "status": "pending"
        }
        
        logging.info(f"Created mock request: {request_id}")
        
        return jsonify({
            "requestId": request_id,
            "message": "Request created successfully",
            "transactionHash": f"0x{uuid.uuid4().hex}"
        }), 200
        
    except Exception as e:
        logging.error(f"Error creating request: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/request/<request_id>', methods=['GET'])
def get_request(request_id):
    """Mock endpoint for getting request status."""
    if request_id in requests_store:
        return jsonify(requests_store[request_id]), 200
    return jsonify({"error": "Request not found"}), 404


@app.route('/api/requests', methods=['GET'])
def list_requests():
    """Mock endpoint for listing all requests."""
    return jsonify(list(requests_store.values())), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "dummy-node-server"}), 200


if __name__ == '__main__':
    print("\n" + "="*50)
    print("  Dummy Node.js Server (Mock Blockchain API)")
    print("="*50)
    print("  Endpoints:")
    print("    POST /api/create     - Create a new request")
    print("    GET  /api/request/<id> - Get request by ID")
    print("    GET  /api/requests   - List all requests")
    print("    GET  /health         - Health check")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=3020, debug=True)
