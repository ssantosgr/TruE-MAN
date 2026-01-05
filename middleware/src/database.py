import sqlite3
import logging

def init_db():
    conn = sqlite3.connect('requests.db')
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
                  tx_hash TEXT UNIQUE,
                  state TEXT DEFAULT 'Pending' CHECK(LOWER(state) IN ('created', 'pending', 'accepted', 'rejected', 'completed')),
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                  
    conn.commit()
    conn.close()
    logging.info("Database initialized.")

def save_request(request_id, private_key=None, contract_address=None, shared_tac=None, ue_imsis_json=None, duration_mins=None, tenant_plmn=None, tenant_amf_ip=None, tenant_amf_port=None, tx_hash=None, state=None):
    try:
        conn = sqlite3.connect('requests.db')
        c = conn.cursor()
        
        # Check if request exists
        c.execute("SELECT 1 FROM requests WHERE id = ?", (request_id,))
        exists = c.fetchone()
        
        if exists:
            # Update existing record
            fields = []
            values = []
            
            if private_key is not None:
                fields.append("private_key = ?")
                values.append(private_key)
            if contract_address is not None:
                fields.append("contract_address = ?")
                values.append(contract_address)
            if shared_tac is not None:
                fields.append("shared_tac = ?")
                values.append(shared_tac)
            if ue_imsis_json is not None:
                fields.append("ue_imsis_json = ?")
                values.append(ue_imsis_json)
            if duration_mins is not None:
                fields.append("duration_mins = ?")
                values.append(duration_mins)
            if tenant_plmn is not None:
                fields.append("tenant_plmn = ?")
                values.append(tenant_plmn)
            if tenant_amf_ip is not None:
                fields.append("tenant_amf_ip = ?")
                values.append(tenant_amf_ip)
            if tenant_amf_port is not None:
                fields.append("tenant_amf_port = ?")
                values.append(tenant_amf_port)
            if tx_hash is not None:
                fields.append("tx_hash = ?")
                values.append(tx_hash)
            if state is not None:
                fields.append("state = ?")
                values.append(state)
            
            if fields:
                values.append(request_id)
                query = f"UPDATE requests SET {', '.join(fields)} WHERE id = ?"
                c.execute(query, tuple(values))
                logging.info(f"Request {request_id} updated in database.")
            else:
                logging.info(f"Request {request_id} exists, no fields to update.")

        else:
            # Insert new record
            state_val = state if state is not None else 'Pending'
            c.execute('''INSERT INTO requests 
                         (id, private_key, contract_address, shared_tac, ue_imsis_json, duration_mins, tenant_plmn, tenant_amf_ip, tenant_amf_port, tx_hash, state) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (request_id, private_key, contract_address, shared_tac, ue_imsis_json, duration_mins, tenant_plmn, tenant_amf_ip, tenant_amf_port, tx_hash, state_val))
            logging.info(f"Request {request_id} saved to database.")

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error saving request: {e}")
        return False

def get_request_id_by_tx_hash(tx_hash):
    try:
        conn = sqlite3.connect('requests.db')
        c = conn.cursor()
        c.execute("SELECT id FROM requests WHERE tx_hash = ?", (tx_hash,))
        row = c.fetchone()
        conn.close()
        if row:
            return row[0]
        return None
    except Exception as e:
        logging.error(f"Error getting request ID by tx_hash: {e}")
        return None
