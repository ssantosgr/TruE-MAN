import json
import logging
from typing import Optional, List, Dict, Any

import requests

# Constants
DEFAULT_GNB_ID = '1'
CONTENT_TYPE_JSON = {"Content-Type": "application/json"}

# Parameter name mapping for restart action
RESTART_PARAM_MAPPING = {
    'amf_addr_tenant': 'PRMT_AMF_ADDR_TENANT',
    'nssai_tenant': 'PRMT_NSSAI_TENANT',
    'plmn_tenant': 'PRMT_PLMN_TENANT',
    'tac_tenant': 'PRMT_TAC_TENANT',
}

# Non-tenant parameter mapping for restart action
NON_TENANT_PARAM_MAPPING = {
    'gtp_addr': 'PRMT_GTP_ADDR',
    'tdd_config': 'PRMT_TDD_CONFIG',
    'amf_addr': 'PRMT_AMF_ADDR',
    'nssai': 'PRMT_NSSAI',
    'plmn': 'PRMT_PLMN',
    'tac': 'PRMT_TAC',
}


def _build_payload(action: str, action_parameters: Optional[Any] = None) -> dict:
    """Build the agent request payload."""
    payload = {
        "activation_feature": [{
            "name": "gNodeB_service",
            "feature_characteristic": [
                {"name": "action", "value": {"value": action}}
            ]
        }]
    }
    if action_parameters:
        payload["activation_feature"][0]["feature_characteristic"].append(
            {"name": "action_parameters", "value": {"value": action_parameters}}
        )
    return payload


def _create_error_response(status_code: int = 500, message: str = "Internal Server Error") -> requests.Response:
    """Create an error response object."""
    response = requests.Response()
    response.status_code = status_code
    response._content = message.encode('utf-8')
    return response


def call_agent(action: str, agent_url: str, action_parameters: Optional[Any] = None, timeout: int = 30) -> requests.Response:
    """Send a request to the agent.
    
    Args:
        action: The action to perform (e.g., 'restart', 'get_all_ues', 'update_ues')
        agent_url: Base URL of the agent (e.g., http://localhost:4000)
        action_parameters: Optional parameters for the action
        timeout: Request timeout in seconds (default: 30)
    
    Returns:
        Response object from the agent
    """
    url = f"{agent_url.rstrip('/')}/resource/{DEFAULT_GNB_ID}"
    payload = _build_payload(action, action_parameters)
    
    logging.info(f"Sending action '{action}' to {url} with params: {action_parameters} and payload: {json.dumps(payload)}")
    
    try:
        response = requests.patch(url, headers=CONTENT_TYPE_JSON, data=json.dumps(payload), timeout=timeout)
        response.raise_for_status()
        
        logging.info(f"Agent responded with status {response.status_code}: {response.text}")
        return response
    
    except requests.exceptions.Timeout:
        logging.error(f"Request to agent at {url} timed out after {timeout}s")
        return _create_error_response(504, "Agent request timed out")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to call agent at {url}: {e}")
        return _create_error_response()


def call_agent_restart(agent_url: str, non_tenant_config: Optional[Dict] = None, **kwargs) -> requests.Response:
    """Send a restart request to the agent with tenant and non-tenant configuration.
    
    Args:
        agent_url: Base URL of the agent
        non_tenant_config: Dictionary with non-tenant params (gtp_addr, tdd_config, amf_addr, nssai, plmn, tac)
        **kwargs: Tenant parameters (amf_addr_tenant, nssai_tenant, plmn_tenant, tac_tenant)
    """
    action_parameters = {}
    
    # Add non-tenant parameters
    if non_tenant_config:
        for k, v in non_tenant_config.items():
            if k in NON_TENANT_PARAM_MAPPING and v is not None:
                action_parameters[NON_TENANT_PARAM_MAPPING[k]] = v
    
    # Add tenant parameters
    for k, v in kwargs.items():
        if k in RESTART_PARAM_MAPPING and v is not None:
            action_parameters[RESTART_PARAM_MAPPING[k]] = v
    
    return call_agent('restart', agent_url, action_parameters or None)


def call_agent_get_all_ues(agent_url: str) -> requests.Response:
    """Get all UEs from the agent."""
    return call_agent('get_all_ues', agent_url)


def call_agent_update_ues(agent_url: str, ues: List[Dict]) -> requests.Response:
    """Update UEs on the agent.
    
    Args:
        agent_url: Base URL of the agent
        ues: List of UE dictionaries containing sim_algo, imsi, opc, amf, sqn, K,
             pdn_list, impi, impu, and allowed_5gs_tais
    """
    return call_agent('update_ues', agent_url, ues)
