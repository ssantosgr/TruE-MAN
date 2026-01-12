from flask import Blueprint, request, jsonify, current_app
import logging
import uuid
import json
import requests
from database import save_request, get_request_id_by_tx_hash, get_request_data_by_tx_hash
from utils import call_agent_restart, call_agent_get_all_ues, call_agent_update_ues

api = Blueprint('api', __name__)

@api.route('/api/create', methods=['POST'])
def create_request():
    try:
        # Parse JSON payload
        try:
            data = request.get_json()
        except Exception as e:
            logging.error(f"Failed to parse JSON: {e}")
            return jsonify({"error": "Invalid JSON format"}), 400
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract and validate required fields
        private_key = data.get('privateKey')
        contract_address = data.get('contractAddress')
        shared_TAC = data.get('sharedTAC')
        ue_imsis = data.get('ueImsis', [])
        
        if not private_key or not contract_address or not shared_TAC or not ue_imsis:
            return jsonify({"error": "Missing one of required fields: privateKey, contractAddress, sharedTAC, or ueImsis"}), 400
        
        # Store IMSIs as JSON list string
        ue_imsi_str = json.dumps(ue_imsis) if ue_imsis else None
        duration_mins = data.get('durationMins')
        
        tenant_PLMN = data.get('tenantPLMN')
        tenant_AMF_IP = data.get('tenantAMFIP')
        tenant_AMF_port = data.get('tenantAMFPort')
        tenant_NSSAI = data.get('tenantNSSAI')
        # Store tenant NSSAI as JSON list string
        tenant_nssai_str = json.dumps(tenant_NSSAI) if tenant_NSSAI else None

        # Save to DB
        request_id = str(uuid.uuid4())
        save_request(
            request_id=request_id,
            state='Created',
            private_key=private_key,
            contract_address=contract_address,
            shared_tac=shared_TAC,
            ue_imsis_json=ue_imsi_str,
            duration_mins=duration_mins,
            tenant_plmn=tenant_PLMN,
            tenant_amf_ip=tenant_AMF_IP,
            tenant_amf_port=tenant_AMF_port,
            tenant_nssai_json=tenant_nssai_str
        )
        logging.info(f"Received create request: {data}")

        # Forward to Node.js server
        number_of_users = len(ue_imsis) if ue_imsis else 1
        payload = {
            "privateKey": private_key,
            "contractAddress": contract_address,
            "numUsers": number_of_users,
            "durationMins": duration_mins
        }
        node_server_base_url = current_app.config.get('NODE_SERVER_URL', "http://localhost:3020/api")
        node_server_url = f"{node_server_base_url}/create"
        response = requests.post(node_server_url, json=payload)
        
        if response.status_code != 200:
            logging.error(f"Node.js server returned status {response.status_code}")
            return jsonify({"error": "Failed to process request on Node.js server"}), 500
        
        response_data = response.json()
        tx_hash = response_data.get('txHash')
        if not tx_hash:
            logging.error("Node.js server returned 200 but no txHash")
            return jsonify({"error": "No transaction hash received from server"}), 500
        
        save_request(request_id, tx_hash=tx_hash, state='Pending')
        return jsonify(response_data), 200

    except requests.exceptions.RequestException as e:
        logging.error(f"Error forwarding to Node.js: {e}")
        return jsonify({"error": "Failed to forward request"}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

@api.route('/api/request/<tx_hash>/<state>', methods=['PATCH'])
def update_request_state(tx_hash, state):
    try:
        # Validate state parameter
        valid_states = ['accepted', 'rejected', 'completed']
        if state.lower() not in valid_states:
            return jsonify({"error": f"Invalid state. Must be one of: {', '.join(valid_states)}"}), 400
        
        # Try to resolve UUID from tx_hash
        request_id = get_request_id_by_tx_hash(tx_hash)
        if not request_id:
            return jsonify({"error": f"Request with tx_hash '{tx_hash}' not found"}), 404

        # Update state in DB
        try:
            if state.lower() != 'accepted':
                save_request(request_id, state=state.capitalize())
                logging.info(f"Request {request_id} (tx_hash: {tx_hash}) state updated to: {state.capitalize()}")
            
            if state.lower() == 'accepted':
                # Get request data from DB to pass to the agent
                request_data = get_request_data_by_tx_hash(tx_hash)
                if not request_data:
                    logging.error(f"Failed to retrieve request data for tx_hash {tx_hash}")
                    return jsonify({"error": "Failed to retrieve request data"}), 500
                
                # Call the agent to restart the service with tenant configuration
                agent_url = current_app.config.get('AGENT_URL', 'http://localhost:4000/resource/1')
                
                # Parse tenant NSSAI JSON if it exists
                nssai_tenant = json.loads(request_data.get('tenant_nssai_json')) if request_data.get('tenant_nssai_json') else None
                
                # Build AMF address with port for tenant if both IP and port exist
                tenant_amf_addr = None
                if request_data.get('tenant_amf_ip'):
                    if request_data.get('tenant_amf_port'):
                        tenant_amf_addr = f"{request_data.get('tenant_amf_ip')}:{request_data.get('tenant_amf_port')}"
                    else:
                        tenant_amf_addr = request_data.get('tenant_amf_ip')
                
                response = call_agent_restart(
                    agent_url=agent_url,
                    amf_addr_tenant=tenant_amf_addr,
                    nssai_tenant=nssai_tenant,
                    plmn_tenant=request_data.get('tenant_plmn'),
                    tac_tenant=int(request_data.get('shared_tac')) if request_data.get('shared_tac') else None
                )
                if response.status_code != 200:
                    logging.error(f"Failed to restart service on agent for request {request_id}")
                    return jsonify({"error": "Failed to restart service on agent"}), 500
                
                # Get all UEs and update TAC restrictions for UEs not in ue_imsis
                ues_response = call_agent_get_all_ues(agent_url)
                if ues_response.status_code == 200:
                    try:
                        ues_data = ues_response.json()
                        all_ues = ues_data.get('ues', [])
                        
                        # Get ue_imsis from request data
                        ue_imsis = json.loads(request_data.get('ue_imsis_json', '[]')) if request_data.get('ue_imsis_json') else []
                        shared_tac = int(request_data.get('shared_tac')) if request_data.get('shared_tac') else None
                        
                        # Filter UEs whose IMSI is NOT in ue_imsis
                        ues_to_update = []
                        for ue in all_ues:
                            if ue.get('imsi') not in ue_imsis:
                                # Add shared TAC to the allowed_5gs_tais restriction
                                if 'allowed_5gs_tais' not in ue:
                                    ue['allowed_5gs_tais'] = {
                                        "restriction_type": "not_allowed",
                                        "tais": [{"plmn": request_data.get('tenant_plmn', '00101'), "areas": [{"tacs": []}]}]
                                    }
                                
                                # Add shared_tac to the tacs list if not already present
                                if shared_tac:
                                    for tai in ue['allowed_5gs_tais'].get('tais', []):
                                        for area in tai.get('areas', []):
                                            if shared_tac not in area.get('tacs', []):
                                                area.setdefault('tacs', []).append(shared_tac)
                                
                                ues_to_update.append(ue)
                        
                        # Update UEs with modified TAC restrictions
                        if ues_to_update:
                            update_response = call_agent_update_ues(agent_url, ues_to_update)
                                
                            if update_response.status_code != 200:
                                logging.error(f"Failed to update UEs TAC restrictions for request {request_id}")
                                save_request(request_id, state='Accepted')
                                logging.info(f"Request {request_id} state updated to Accepted (UE update failed)")
                            else:
                                logging.info(f"Updated TAC restrictions for {len(ues_to_update)} UEs")
                                save_request(request_id, state='Completed')
                                logging.info(f"Request {request_id} state updated to Completed")
                        else:
                            # No UEs to update, mark as completed
                            save_request(request_id, state='Completed')
                            logging.info(f"Request {request_id} state updated to Completed (no UEs to update)")
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to parse UEs response: {e}")
                        save_request(request_id, state='Accepted')
                        logging.info(f"Request {request_id} state updated to Accepted (parse error)")
                else:
                    logging.error(f"Failed to get all UEs from agent: {ues_response.status_code}")
                    save_request(request_id, state='Accepted')
                    logging.info(f"Request {request_id} state updated to Accepted (get UEs failed)")
            
            return jsonify({
                "success": True,
                "message": f"Request state updated to {state.capitalize()}",
                "txHash": tx_hash,
                "state": state.capitalize()
            }), 200
            
        except Exception as e:
            logging.error(f"Error updating request state: {e}")
            return jsonify({"error": "Failed to update request state"}), 500

    except Exception as e:
        logging.error(f"Unexpected error in update_request_state: {e}")
        return jsonify({"error": str(e)}), 500