"""Request creation service."""
import logging
import uuid
import json
import requests
from database import save_request


# Required fields for request creation
REQUIRED_FIELDS = ('privateKey', 'contractAddress', 'sharedTAC', 'ueImsis')


def validate_create_request_data(data):
    """Validate request creation payload.
    
    Args:
        data: Request payload dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not data:
        return False, "No JSON data provided"
    
    missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    
    return True, None


def extract_and_save_request_data(data):
    """Extract data from request and save to database.
    
    Args:
        data: Request payload dictionary
        
    Returns:
        Tuple of (request_id, ue_imsis list)
    """
    ue_imsis = data.get('ueImsis', [])
    tenant_nssai = data.get('tenantNSSAI')
    
    request_id = str(uuid.uuid4())
    save_request(
        request_id=request_id,
        state='Created',
        private_key=data.get('privateKey'),
        contract_address=data.get('contractAddress'),
        shared_tac=data.get('sharedTAC'),
        ue_imsis_json=json.dumps(ue_imsis) if ue_imsis else None,
        duration_mins=data.get('durationMins'),
        tenant_plmn=data.get('tenantPLMN'),
        tenant_amf_ip=data.get('tenantAMFIP'),
        tenant_amf_port=data.get('tenantAMFPort'),
        tenant_nssai_json=json.dumps(tenant_nssai) if tenant_nssai else None
    )
    
    logging.info(f"Created request {request_id}")
    return request_id, ue_imsis


def forward_to_node_server(private_key, contract_address, ue_imsis, duration_mins, node_server_url):
    """Forward request to Node.js blockchain server.
    
    Args:
        private_key: Blockchain private key
        contract_address: Smart contract address
        ue_imsis: List of UE IMSIs
        duration_mins: Duration in minutes
        node_server_url: Base URL of the Node.js server
        
    Returns:
        Tuple of (external_request_id, response_data)
        
    Raises:
        Exception: If the server returns an error or no request ID
    """
    payload = {
        "privateKey": private_key,
        "contractAddress": contract_address,
        "numUsers": len(ue_imsis) if ue_imsis else 1,
        "durationMins": duration_mins
    }
    
    response = requests.post(f"{node_server_url}/create", json=payload)
    
    if response.status_code != 200:
        logging.error(f"Node.js server returned status {response.status_code}")
        raise Exception("Failed to process request on Node.js server")
    
    response_data = response.json()
    external_request_id = response_data.get('requestId')
    
    if not external_request_id:
        logging.error("Node.js server returned 200 but no requestId")
        raise Exception("No request ID received from server")
    
    return external_request_id, response_data


def create_request_handler(data, node_server_url):
    """Main handler for request creation.
    
    Validates the request data, saves it to the database, and forwards
    the request to the Node.js blockchain server.
    
    Args:
        data: Request payload dictionary containing privateKey, contractAddress,
              sharedTAC, ueImsis, and optional fields
        node_server_url: Base URL of the Node.js server
        
    Returns:
        Tuple of (response_data, error_message, status_code):
        - On success: (response_data dict, None, 200)
        - On validation error: (None, error_message, 400)
        - On server/network error: (None, error_message, 500)
    """
    # Validate data
    valid, error_msg = validate_create_request_data(data)
    if not valid:
        return None, error_msg, 400
    
    # Extract and save to DB
    request_id, ue_imsis = extract_and_save_request_data(data)
    
    # Forward to Node.js server
    try:
        external_requestId, response_data = forward_to_node_server(
            data.get('privateKey'),
            data.get('contractAddress'),
            ue_imsis,
            data.get('durationMins'),
            node_server_url
        )
        
        # Update DB with external request ID
        save_request(request_id, external_requestId=external_requestId, state='Pending')
        
        return response_data, None, 200
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error forwarding to Node.js: {e}")
        return None, "Failed to forward request", 500
    except Exception as e:
        logging.error(f"Error in request creation: {e}")
        return None, str(e), 500
