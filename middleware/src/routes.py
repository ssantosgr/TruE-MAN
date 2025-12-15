from flask import Blueprint, request, jsonify, current_app
import logging
import sqlite3
import uuid
import requests
from database import save_request, get_request_id_by_sc_id

api = Blueprint('api', __name__)

@api.route('/api/create', methods=['POST'])
def create_request():
    try:
        # Payload corresponding to the JS function
        data = request.get_json()
        
        # Extracting fields as per the requirement
        private_key = data.get('privateKey')
        contract_address = data.get('contractAddress')
        duration_mins = data.get('durationMins')
        
        ue_details = data.get('ueDetails', {})
        ue_imsi = ue_details.get('ueImsi')
        ue_K = ue_details.get('ueK')
        ue_opc = ue_details.get('ueOpc')
        
        tenant_PLMN = data.get('tenantPLMN')
        tenant_AMF_IP = data.get('tenantAMFIP')
        tenant_AMF_port = data.get('tenantAMFPort')

        # Save to DB
        request_id = str(uuid.uuid4())
        save_request(request_id, private_key, contract_address, duration_mins, ue_imsi, ue_K, ue_opc, tenant_PLMN, tenant_AMF_IP, tenant_AMF_port)
        
        logging.info(f"Received create request: {data}")

        # Forward to Node.js server
        try:
            payload = {
                "privateKey": private_key,
                "contractAddress": contract_address,
                "numUsers": data.get('numUsers', 1),
                "durationMins": duration_mins,
                "offChainData": request_id
            }
            node_server_base_url = current_app.config.get('NODE_SERVER_URL', "http://localhost:3020/api")
            node_server_url = f"{node_server_base_url}/create"
            response = requests.post(node_server_url, json=payload)            
            if response.status_code == 200:
                response_data = response.json()
                sc_request_id = response_data.get('requestId')
                if sc_request_id:
                    save_request(request_id, sc_request_id=sc_request_id)
                    return jsonify(response.json()), response.status_code
        except requests.exceptions.RequestException as e:
            logging.error(f"Error forwarding to Node.js: {e}")
            return jsonify({"error": "Failed to forward request"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/api/status', methods=['POST'])
def status_endpoint():
    try:
        data = request.get_json()
        accepted = data.get('accepted')
        request_id_param = data.get('requestId')
        
        if accepted is None:
            save_request(request_id_param, accepted='FAILED')
            return jsonify({"error": "Missing 'accepted' field"}), 400

        # Try to resolve UUID from SC ID
        request_id = get_request_id_by_sc_id(str(request_id_param))
        if not request_id:
            return jsonify({"error": "Missing 'requestId' field"}), 400

        # Update status in DB
        save_request(request_id, accepted=accepted)

        
        
        logging.info(f"Received success status: {accepted}")

        return jsonify({
            "success": True,
            "message": "Status received"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
