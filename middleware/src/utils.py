import requests
import json
from typing import Optional
import logging

def call_agent(action: str, agent_url: str, action_parameters: Optional[dict] = None) -> requests.Response:
    """Constructs and sends a request to the agent."""
    
    gnb_id = '1'
    agent_url = agent_url.rstrip('/') + '/resource/' + gnb_id
    
    payload = {
        "activation_feature": [
            {
                "name": "gNodeB_service",
                "feature_characteristic": [
                    {"name": "action", 
                     "value": {
                         "value": action}
                     }
                ]
            }
        ]
    }
    if action_parameters:
        payload["activation_feature"][0]["feature_characteristic"].append(
            {"name": "action_parameters", 
             "value": 
                 {"value": action_parameters}}
        )

    headers = {"Content-Type": "application/json"}
    logging.info(f"Sending action '{action}' to {agent_url} with params: {action_parameters}")
    try:
        response = requests.patch(agent_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        if response.status_code == 200:
            success_message = f"Action '{action}' executed successfully."
            response._content = success_message.encode('utf-8')
            logging.info(f"Agent responded with status {response.status_code}: {response.text}")
        else:
            logging.info(f"Agent responded with status {response.status_code}: {response.text}")
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to call agent at {agent_url}: {e}")
        response = requests.Response()
        response.status_code = 500
        response._content = b"Internal Server Error"
        return response

def call_agent_restart(agent_url: str, amf_addr_tenant: Optional[str] = None, 
                       nssai_tenant: Optional[list] = None, plmn_tenant: Optional[str] = None,
                       tac_tenant: Optional[int] = None) -> requests.Response:
    """Constructs and sends a restart request to the agent with tenant configuration parameters.
    Only includes parameters that are provided (not None)."""
    
    # Build action_parameters dict only with provided values
    action_parameters = {}
    if amf_addr_tenant is not None:
        action_parameters["PRMT_AMF_ADDR_TENANT"] = amf_addr_tenant
    if nssai_tenant is not None:
        action_parameters["PRMT_NSSAI_TENANT"] = nssai_tenant
    if plmn_tenant is not None:
        action_parameters["PRMT_PLMN_TENANT"] = plmn_tenant
    if tac_tenant is not None:
        action_parameters["PRMT_TAC_TENANT"] = tac_tenant
    
    # Use call_agent with action='restart' and the built parameters
    return call_agent(
        action='restart',
        agent_url=agent_url,
        action_parameters=action_parameters if action_parameters else None
    )
