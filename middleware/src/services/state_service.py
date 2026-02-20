"""State update service."""
import logging
from database import save_request, get_request_data_by_external_requestId, get_request_id_by_external_requestId
from services.agent_service import restart_agent_with_tenant_config, get_and_update_ue_restrictions
from services.config_service import schedule_configuration_restoration


VALID_STATES = ['accepted', 'rejected', 'completed']


def validate_state(state):
    """Validate state parameter."""
    if state.lower() not in VALID_STATES:
        return False, f"Invalid state. Must be one of: {', '.join(VALID_STATES)}"
    return True, None


def handle_non_accepted_state(request_id, external_requestId, state):
    """Handle rejected or completed state updates."""
    save_request(request_id, state=state.capitalize())
    logging.info(f"Request {request_id} (external_requestId: {external_requestId}) state updated to: {state.capitalize()}")
    return True


def handle_accepted_state(request_id, external_requestId, agent_url, non_tenant_config=None):
    """Handle accepted state with full configuration update."""
    # Get request data from DB
    request_data = get_request_data_by_external_requestId(external_requestId)
    if not request_data:
        logging.error(f"Failed to retrieve request data for external_requestId {external_requestId}")
        return False, "Failed to retrieve request data"
    
    # Restart agent with tenant configuration
    if not restart_agent_with_tenant_config(agent_url, request_data, non_tenant_config):
        return False, "Failed to restart service on agent"
    
    # Get and update UE restrictions
    success, original_ues, num_updated = get_and_update_ue_restrictions(agent_url, request_data)
    
    if not success:
        save_request(request_id, state='Accepted')
        logging.info(f"Request {request_id} state updated to Accepted (UE update failed)")
        return True, None
    
    # Mark as completed
    save_request(request_id, state='Completed')
    logging.info(f"Request {request_id} state updated to Completed")
    
    # Schedule restoration if duration is specified
    duration_mins = request_data.get('duration_mins')
    shared_tac = request_data.get('shared_tac')
    tenant_plmn = request_data.get('tenant_plmn')
    
    if duration_mins:
        schedule_configuration_restoration(
            request_id, 
            external_requestId, 
            agent_url, 
            non_tenant_config,
            shared_tac,
            tenant_plmn,
            duration_mins
        )
    
    return True, None


def update_request_state_handler(external_requestId, state, agent_url, non_tenant_config=None):
    """Main handler for state update operations.
    
    Args:
        external_requestId: External request ID
        state: New state (accepted/rejected/completed)
        agent_url: Base URL of the agent
        non_tenant_config: Dictionary with non-tenant params (gtp_addr, tdd_config, amf_addr, nssai, plmn, tac)
    """
    # Validate state
    valid, error_msg = validate_state(state)
    if not valid:
        return None, error_msg, 400
    
    # Get request ID
    request_id = get_request_id_by_external_requestId(external_requestId)
    if not request_id:
        return None, f"Request with external_requestId '{external_requestId}' not found", 404
    
    try:
        # Handle different states
        if state.lower() != 'accepted':
            handle_non_accepted_state(request_id, external_requestId, state)
            success = True
            error = None
        else:
            success, error = handle_accepted_state(request_id, external_requestId, agent_url, non_tenant_config)
        
        if not success:
            return None, error or "Failed to update request state", 500
        
        return {
            "success": True,
            "message": f"Request state updated to {state.capitalize()}",
            "external_requestId": external_requestId,
            "state": state.capitalize()
        }, None, 200
        
    except Exception as e:
        logging.error(f"Error updating request state: {e}")
        return None, "Failed to update request state", 500
