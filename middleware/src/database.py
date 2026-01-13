import sqlite3
import logging
import os
from typing import Optional

# Database path relative to middleware directory
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BASE_DIR, 'data')
DB_PATH = os.path.join(_DATA_DIR, 'requests.db')

# Fields that can be updated in the requests table
UPDATABLE_FIELDS = {
    'private_key', 'contract_address', 'shared_tac', 'ue_imsis_json',
    'duration_mins', 'tenant_plmn', 'tenant_amf_ip', 'tenant_amf_port',
    'tenant_nssai_json', 'gtp_addr', 'tdd_config', 'amf_addr',
    'nssai_json', 'plmn', 'tac', 'external_requestId', 'state'
}

def init_db():
    # Ensure data directory exists
    os.makedirs(_DATA_DIR, exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS requests
                     (id TEXT PRIMARY KEY,
                      private_key TEXT NOT NULL,
                      contract_address TEXT NOT NULL,
                      shared_tac TEXT NOT NULL,
                      ue_imsis_json TEXT NOT NULL,
                      duration_mins INTEGER,
                      tenant_plmn TEXT,
                      tenant_amf_ip TEXT,
                      tenant_amf_port INTEGER,
                      tenant_nssai_json TEXT,
                      gtp_addr TEXT,
                      tdd_config INTEGER,
                      amf_addr TEXT,
                      nssai_json TEXT,
                      plmn TEXT,
                      tac INTEGER,
                      external_requestId TEXT UNIQUE,
                      state TEXT DEFAULT 'Pending' CHECK(LOWER(state) IN ('created', 'pending', 'accepted', 'rejected', 'completed')),
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
    logging.info("Database initialized.")

def save_request(request_id: str, **kwargs) -> bool:
    """Save or update a request. Pass fields as keyword arguments."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT 1 FROM requests WHERE id = ?", (request_id,))
            exists = c.fetchone()
            
            if exists:
                # Build update from provided kwargs
                fields = {k: v for k, v in kwargs.items() if k in UPDATABLE_FIELDS and v is not None}
                if fields:
                    query = f"UPDATE requests SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?"
                    c.execute(query, (*fields.values(), request_id))
                    logging.info(f"Request {request_id} updated in database.")
                else:
                    logging.info(f"Request {request_id} exists, no fields to update.")
            else:
                # Insert new record with defaults
                kwargs.setdefault('state', 'Pending')
                columns = ['id'] + [k for k in UPDATABLE_FIELDS if k in kwargs]
                values = [request_id] + [kwargs[k] for k in UPDATABLE_FIELDS if k in kwargs]
                placeholders = ', '.join('?' * len(columns))
                query = f"INSERT INTO requests ({', '.join(columns)}) VALUES ({placeholders})"
                c.execute(query, values)
                logging.info(f"Request {request_id} saved to database.")
            
            conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error saving request: {e}")
        return False

def get_request_id_by_external_requestId(external_requestId: str) -> Optional[str]:
    """Get request ID by transaction hash."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM requests WHERE external_requestId = ?", (external_requestId,))
            row = c.fetchone()
            return row[0] if row else None
    except Exception as e:
        logging.error(f"Error getting request ID by external_requestId: {e}")
        return None

def get_request_data_by_external_requestId(external_requestId: str) -> Optional[dict]:
    """Get full request data by transaction hash."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM requests WHERE external_requestId = ?", (external_requestId,))
            row = c.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logging.error(f"Error getting request data by external_requestId: {e}")
        return None
