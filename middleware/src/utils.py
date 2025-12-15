import requests
import json
from typing import Optional
import logging

def call_agent(action: str, agent_url: str, action_parameters: Optional[dict] = None) -> requests.Response:
    """Constructs and sends a request to the agent."""
    
    gnb_id = agent_url.split(".")[-1].split(":")[0]
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
        response.raise_for_status()  # Raise an exception for bad status codes
        if(response.status_code == 200):
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
