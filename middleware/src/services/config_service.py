"""Configuration management and restoration service."""
import logging
import time
import threading
from database import save_request
from utils import call_agent_restart, call_agent_update_ues


def restore_configuration(request_id, external_requestId, agent_url, original_ues, duration_mins):
    """Restore UE configuration to original state after duration expires."""
    try:
        logging.info(f"Waiting {duration_mins} minutes before restoring configuration for request {request_id}")
        # Wait for the duration to expire
        time.sleep(duration_mins * 60)
        
        logging.info(f"Duration expired, restoring configuration for request {request_id}")
        
        # First, restart the agent with null tenant values to restore original configuration
        restart_response = call_agent_restart(
            agent_url=agent_url,
            amf_addr_tenant=None,
            nssai_tenant=None,
            plmn_tenant=None,
            tac_tenant=None
        )
        
        if restart_response.status_code != 200:
            logging.error(f"Failed to restart agent with null tenant values for request {request_id}: {restart_response.status_code}")
            save_request(request_id, state='RestoreFailed')
            return
        
        logging.info(f"Successfully restarted agent with null tenant values for request {request_id}")
        
        # Then restore the original UE configurations
        if original_ues:
            update_response = call_agent_update_ues(agent_url, original_ues)
            
            if update_response.status_code == 200:
                logging.info(f"Successfully restored {len(original_ues)} UEs to original configuration")
                save_request(request_id, state='Expired')
                logging.info(f"Request {request_id} state updated to Expired")
            else:
                logging.error(f"Failed to restore UE configurations for request {request_id}: {update_response.status_code}")
                save_request(request_id, state='RestoreFailed')
        else:
            logging.info(f"No UEs to restore for request {request_id}")
            save_request(request_id, state='Expired')
            
    except Exception as e:
        logging.error(f"Error in restore_configuration for request {request_id}: {e}")
        try:
            save_request(request_id, state='RestoreFailed')
        except:
            pass


def schedule_configuration_restoration(request_id, external_requestId, agent_url, original_ues, duration_mins):
    """Schedule a background thread to restore configuration after duration."""
    if duration_mins and duration_mins > 0:
        restore_thread = threading.Thread(
            target=restore_configuration,
            args=(request_id, external_requestId, agent_url, original_ues, duration_mins),
            daemon=True
        )
        restore_thread.start()
        logging.info(f"Scheduled configuration restoration in {duration_mins} minutes for request {request_id}")
