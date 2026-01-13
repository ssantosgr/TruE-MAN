import pytest
import os
import sqlite3
import tempfile
from unittest.mock import patch

# Patch DB_PATH before importing database module
@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    """Use a temporary database for each test."""
    test_db_path = str(tmp_path / 'test_requests.db')
    test_data_dir = str(tmp_path)
    
    with patch('database._DATA_DIR', test_data_dir), \
         patch('database.DB_PATH', test_db_path):
        # Import after patching
        import database
        database._DATA_DIR = test_data_dir
        database.DB_PATH = test_db_path
        database.init_db()
        yield database
        

class TestInitDb:
    def test_creates_data_directory(self, temp_db, tmp_path):
        """Test that init_db creates the data directory."""
        assert os.path.exists(tmp_path)
    
    def test_creates_requests_table(self, temp_db):
        """Test that init_db creates the requests table with correct schema."""
        with sqlite3.connect(temp_db.DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requests'")
            assert c.fetchone() is not None
    
    def test_table_has_correct_columns(self, temp_db):
        """Test that the requests table has all expected columns."""
        expected_columns = {
            'id', 'private_key', 'contract_address', 'shared_tac', 'ue_imsis_json',
            'duration_mins', 'tenant_plmn', 'tenant_amf_ip', 'tenant_amf_port',
            'tenant_nssai_json', 'gtp_addr', 'tdd_config', 'amf_addr', 'nssai_json',
            'plmn', 'tac', 'tx_hash', 'state', 'created_at'
        }
        with sqlite3.connect(temp_db.DB_PATH) as conn:
            c = conn.cursor()
            c.execute("PRAGMA table_info(requests)")
            actual_columns = {row[1] for row in c.fetchall()}
        
        assert expected_columns == actual_columns


class TestSaveRequest:
    def test_insert_new_request(self, temp_db):
        """Test inserting a new request."""
        result = temp_db.save_request(
            request_id='test-123',
            private_key='pk_test',
            contract_address='0xabc',
            shared_tac='101',
            ue_imsis_json='["imsi1"]'
        )
        assert result is True
        
        # Verify insertion
        with sqlite3.connect(temp_db.DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id, private_key, state FROM requests WHERE id = ?", ('test-123',))
            row = c.fetchone()
        
        assert row is not None
        assert row[0] == 'test-123'
        assert row[1] == 'pk_test'
        assert row[2] == 'Pending'  # Default state
    
    def test_insert_with_custom_state(self, temp_db):
        """Test inserting a request with a custom state."""
        temp_db.save_request(
            request_id='test-456',
            private_key='pk_test',
            contract_address='0xabc',
            shared_tac='101',
            ue_imsis_json='["imsi1"]',
            state='Created'
        )
        
        with sqlite3.connect(temp_db.DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT state FROM requests WHERE id = ?", ('test-456',))
            row = c.fetchone()
        
        assert row[0] == 'Created'
    
    def test_update_existing_request(self, temp_db):
        """Test updating an existing request."""
        # Insert first
        temp_db.save_request(
            request_id='test-789',
            private_key='pk_test',
            contract_address='0xabc',
            shared_tac='101',
            ue_imsis_json='["imsi1"]'
        )
        
        # Update
        result = temp_db.save_request(
            request_id='test-789',
            state='Accepted',
            tx_hash='0xhash123'
        )
        assert result is True
        
        # Verify update
        with sqlite3.connect(temp_db.DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT state, tx_hash FROM requests WHERE id = ?", ('test-789',))
            row = c.fetchone()
        
        assert row[0] == 'Accepted'
        assert row[1] == '0xhash123'
    
    def test_update_with_no_fields_to_update(self, temp_db):
        """Test updating when no valid fields are provided."""
        temp_db.save_request(
            request_id='test-noupdate',
            private_key='pk_test',
            contract_address='0xabc',
            shared_tac='101',
            ue_imsis_json='["imsi1"]'
        )
        
        # Update with invalid field
        result = temp_db.save_request(
            request_id='test-noupdate',
            invalid_field='value'
        )
        assert result is True  # Should still succeed, just no updates
    
    def test_ignores_none_values_on_update(self, temp_db):
        """Test that None values are ignored during updates."""
        temp_db.save_request(
            request_id='test-none',
            private_key='pk_test',
            contract_address='0xabc',
            shared_tac='101',
            ue_imsis_json='["imsi1"]',
            tenant_plmn='00101'
        )
        
        # Update with None value - should not overwrite
        temp_db.save_request(
            request_id='test-none',
            tenant_plmn=None,
            state='Accepted'
        )
        
        with sqlite3.connect(temp_db.DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT tenant_plmn, state FROM requests WHERE id = ?", ('test-none',))
            row = c.fetchone()
        
        assert row[0] == '00101'  # Should remain unchanged
        assert row[1] == 'Accepted'


class TestGetRequestIdByTxHash:
    def test_returns_id_when_found(self, temp_db):
        """Test getting request ID by tx_hash when it exists."""
        temp_db.save_request(
            request_id='test-getid',
            private_key='pk_test',
            contract_address='0xabc',
            shared_tac='101',
            ue_imsis_json='["imsi1"]',
            tx_hash='0xuniquehash'
        )
        
        result = temp_db.get_request_id_by_tx_hash('0xuniquehash')
        assert result == 'test-getid'
    
    def test_returns_none_when_not_found(self, temp_db):
        """Test getting request ID by tx_hash when it doesn't exist."""
        result = temp_db.get_request_id_by_tx_hash('0xnonexistent')
        assert result is None


class TestGetRequestDataByTxHash:
    def test_returns_full_data_when_found(self, temp_db):
        """Test getting full request data by tx_hash."""
        temp_db.save_request(
            request_id='test-fulldata',
            private_key='pk_test',
            contract_address='0xcontract',
            shared_tac='102',
            ue_imsis_json='["imsi1", "imsi2"]',
            tx_hash='0xdatahash',
            tenant_plmn='00101',
            duration_mins=60
        )
        
        result = temp_db.get_request_data_by_tx_hash('0xdatahash')
        
        assert result is not None
        assert isinstance(result, dict)
        assert result['id'] == 'test-fulldata'
        assert result['private_key'] == 'pk_test'
        assert result['contract_address'] == '0xcontract'
        assert result['shared_tac'] == '102'
        assert result['ue_imsis_json'] == '["imsi1", "imsi2"]'
        assert result['tx_hash'] == '0xdatahash'
        assert result['tenant_plmn'] == '00101'
        assert result['duration_mins'] == 60
        assert result['state'] == 'Pending'
    
    def test_returns_none_when_not_found(self, temp_db):
        """Test getting request data by tx_hash when it doesn't exist."""
        result = temp_db.get_request_data_by_tx_hash('0xnonexistent')
        assert result is None


class TestStateValidation:
    def test_valid_states(self, temp_db):
        """Test that all valid states are accepted."""
        valid_states = ['Created', 'Pending', 'Accepted', 'Rejected', 'Completed']
        
        for i, state in enumerate(valid_states):
            result = temp_db.save_request(
                request_id=f'test-state-{i}',
                private_key='pk_test',
                contract_address='0xabc',
                shared_tac='101',
                ue_imsis_json='["imsi1"]',
                state=state
            )
            assert result is True
    
    def test_invalid_state_rejected(self, temp_db):
        """Test that invalid states are rejected by the database."""
        result = temp_db.save_request(
            request_id='test-invalid-state',
            private_key='pk_test',
            contract_address='0xabc',
            shared_tac='101',
            ue_imsis_json='["imsi1"]',
            state='InvalidState'
        )
        # Should fail due to CHECK constraint
        assert result is False
