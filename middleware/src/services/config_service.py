"""Configuration management and restoration service."""
import logging
import time
import threading
from database import save_request
from utils import call_agent_restart, call_agent_update_ues, call_agent_get_all_ues


def _remove_tac_from_ue(ue, tac_to_remove, plmn):
    """Remove a TAC from forbidden_5gs_tais for a UE.
    
    Args:
        ue: UE configuration dictionary (modified in place)
        tac_to_remove: TAC value to remove from forbidden list
        plmn: PLMN to match for removal
        
    Returns:
        True if the UE was modified, False otherwise
    """
    if 'forbidden_5gs_tais' not in ue or not tac_to_remove:
        return False
    
    modified = False
    tais_to_keep = []
    
    for tai in ue['forbidden_5gs_tais']:
        if tai.get('plmn') == plmn:
            areas_to_keep = []
            for area in tai.get('areas', []):
                tacs = area.get('tacs', [])
                if tac_to_remove in tacs:
                    tacs.remove(tac_to_remove)
                    modified = True
                if tacs:  # Keep area only if it still has TACs
                    areas_to_keep.append(area)
            if areas_to_keep:  # Keep TAI only if it still has areas
                tai['areas'] = areas_to_keep
                tais_to_keep.append(tai)
        else:
            tais_to_keep.append(tai)
    
    if tais_to_keep:
        ue['forbidden_5gs_tais'] = tais_to_keep
    elif 'forbidden_5gs_tais' in ue:
        del ue['forbidden_5gs_tais']
        
    return modified


def restore_configuration(request_id, external_requestId, agent_url, non_tenant_config, shared_tac, tenant_plmn, duration_mins):
    """Restore configuration after duration expires.
    
    Args:
        request_id: Internal request ID
        external_requestId: External request ID
        agent_url: Base URL of the agent
        non_tenant_config: Non-tenant gNodeB parameters for restart
        shared_tac: TAC to remove from forbidden lists
        tenant_plmn: PLMN used for the TAC restriction
        duration_mins: Minutes to wait before restoration
    """
    try:
        logging.info(f"Waiting {duration_mins} minutes before restoring configuration for request {request_id}")
        # Wait for the duration to expire
        time.sleep(duration_mins * 60)
        
        logging.info(f"Duration expired, restoring configuration for request {request_id}")
        
        # Restart the agent with only non-tenant config (no tenant values)
        restart_response = call_agent_restart(
            agent_url=agent_url,
            non_tenant_config=non_tenant_config
            # No tenant parameters - restores to non-tenant state
        )
        
        if restart_response.status_code != 200:
            logging.error(f"Failed to restart agent for request {request_id}: {restart_response.status_code}")
            save_request(request_id, state='RestoreFailed')
            return
        
        logging.info(f"Successfully restarted agent without tenant values for request {request_id}")
        
        # Get all UEs and remove the blocked TAC
        ues_response = call_agent_get_all_ues(agent_url)
        
        if ues_response.status_code != 200:
            logging.error(f"Failed to get UEs for restoration: {ues_response.status_code}")
            save_request(request_id, state='RestoreFailed')
            return
        
        try:
            all_ues = ues_response.json().get('ues', [])
            ues_to_update = []
            shared_tac_int = int(shared_tac) if shared_tac else None
            plmn = tenant_plmn or '00101'
            
            for ue in all_ues:
                if _remove_tac_from_ue(ue, shared_tac_int, plmn):
                    ues_to_update.append(ue)
            
            if ues_to_update:
                update_response = call_agent_update_ues(agent_url, ues_to_update)
                
                if update_response.status_code == 200:
                    logging.info(f"Successfully removed TAC {shared_tac} from {len(ues_to_update)} UEs")
                else:
                    logging.error(f"Failed to update UEs for request {request_id}: {update_response.status_code}")
                    save_request(request_id, state='RestoreFailed')
                    return
            else:
                logging.info(f"No UEs needed TAC removal for request {request_id}")
            
            save_request(request_id, state='Expired')
            logging.info(f"Request {request_id} state updated to Expired")
            
        except Exception as e:
            logging.error(f"Failed to parse UEs response during restoration: {e}")
            save_request(request_id, state='RestoreFailed')
            
    except Exception as e:
        logging.error(f"Error in restore_configuration for request {request_id}: {e}")
        try:
            save_request(request_id, state='RestoreFailed')
        except:
            pass


def schedule_configuration_restoration(request_id, external_requestId, agent_url, non_tenant_config, shared_tac, tenant_plmn, duration_mins):
    """Schedule a background thread to restore configuration after duration.
    
    Args:
        request_id: Internal request ID
        external_requestId: External request ID  
        agent_url: Base URL of the agent
        non_tenant_config: Non-tenant gNodeB parameters for restart
        shared_tac: TAC to remove from forbidden lists
        tenant_plmn: PLMN used for the TAC restriction
        duration_mins: Minutes to wait before restoration
    """
    if duration_mins and duration_mins > 0:
        restore_thread = threading.Thread(
            target=restore_configuration,
            args=(request_id, external_requestId, agent_url, non_tenant_config, shared_tac, tenant_plmn, duration_mins),
            daemon=True
        )
        restore_thread.start()
        logging.info(f"Scheduled configuration restoration in {duration_mins} minutes for request {request_id}")
