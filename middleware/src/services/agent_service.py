"""Agent interaction service."""
import logging
import json
from copy import deepcopy
from utils import call_agent_restart, call_agent_get_all_ues, call_agent_update_ues


def _build_tenant_amf_address(request_data):
    """Build AMF address string from IP and optional port."""
    ip = request_data.get('tenant_amf_ip')
    if not ip:
        return None
    port = request_data.get('tenant_amf_port')
    return f"{ip}:{port}" if port else ip


def _parse_json_field(request_data, field_name):
    """Parse a JSON string field from request data."""
    value = request_data.get(field_name)
    return json.loads(value) if value else None


def restart_agent_with_tenant_config(agent_url, request_data, non_tenant_config=None):
    """Restart agent service with tenant and non-tenant configuration.
    
    Args:
        agent_url: Base URL of the agent
        request_data: Dictionary containing tenant configuration
        non_tenant_config: Dictionary with non-tenant params (gtp_addr, tdd_config, amf_addr, nssai, plmn, tac)
        
    Returns:
        True if restart successful, False otherwise
    """
    shared_tac = request_data.get('shared_tac')
    
    response = call_agent_restart(
        agent_url=agent_url,
        non_tenant_config=non_tenant_config,
        amf_addr_tenant=_build_tenant_amf_address(request_data),
        nssai_tenant=_parse_json_field(request_data, 'tenant_nssai_json'),
        plmn_tenant=request_data.get('tenant_plmn'),
        tac_tenant=int(shared_tac) if shared_tac else None
    )
    
    if response.status_code != 200:
        logging.error("Failed to restart service on agent")
        return False
    
    return True


def _add_tac_restriction_to_ue(ue, shared_tac, tenant_plmn):
    """Add TAC restriction to a UE configuration using forbidden_5gs_tais.
    
    Args:
        ue: UE configuration dictionary (modified in place)
        shared_tac: TAC value to add to forbidden list
        tenant_plmn: PLMN for the restriction entry
    """
    if not shared_tac:
        return
    
    plmn = tenant_plmn or '00101'
    
    if 'forbidden_5gs_tais' not in ue:
        ue['forbidden_5gs_tais'] = [{"plmn": plmn, "areas": [{"tacs": [shared_tac]}]}]
        return
    
    # Check if PLMN already exists in forbidden_5gs_tais
    for tai in ue['forbidden_5gs_tais']:
        if tai.get('plmn') == plmn:
            for area in tai.get('areas', []):
                tacs = area.setdefault('tacs', [])
                if shared_tac not in tacs:
                    tacs.append(shared_tac)
            return
    
    # Add new PLMN entry
    ue['forbidden_5gs_tais'].append({"plmn": plmn, "areas": [{"tacs": [shared_tac]}]})


def get_and_update_ue_restrictions(agent_url, request_data):
    """Get all UEs and update TAC restrictions for non-tenant UEs.
    
    Args:
        agent_url: Base URL of the agent
        request_data: Dictionary containing ue_imsis_json, shared_tac, tenant_plmn
        
    Returns:
        Tuple of (success, original_ues, num_updated)
    """
    ues_response = call_agent_get_all_ues(agent_url)
    
    if ues_response.status_code != 200:
        logging.error(f"Failed to get all UEs from agent: {ues_response.status_code}")
        return False, None, None
    
    try:
        all_ues = ues_response.json().get('ues', [])
        tenant_ue_imsis = _parse_json_field(request_data, 'ue_imsis_json') or []
        shared_tac = request_data.get('shared_tac')
        shared_tac_int = int(shared_tac) if shared_tac else None
        tenant_plmn = request_data.get('tenant_plmn')
        
        # Process non-tenant UEs
        original_ues = []
        ues_to_update = []
        
        for ue in all_ues:
            if ue.get('imsi') in tenant_ue_imsis:
                continue
                
            original_ues.append(deepcopy(ue))
            _add_tac_restriction_to_ue(ue, shared_tac_int, tenant_plmn)
            ues_to_update.append(ue)
        
        if not ues_to_update:
            logging.info("No UEs to update")
            return True, [], 0
        
        # Update UEs with modified TAC restrictions
        update_response = call_agent_update_ues(agent_url, ues_to_update)
        
        if update_response.status_code != 200:
            logging.error("Failed to update UEs TAC restrictions")
            return False, None, None
        
        logging.info(f"Updated TAC restrictions for {len(ues_to_update)} UEs")
        return True, original_ues, len(ues_to_update)
            
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse UEs response: {e}")
        return False, None, None
