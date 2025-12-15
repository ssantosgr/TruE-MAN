import sqlite3
import logging

def init_db():
    conn = sqlite3.connect('requests.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                 (id TEXT PRIMARY KEY,
                  private_key TEXT,
                  contract_address TEXT,
                  duration_mins TEXT,
                  ue_imsi TEXT,
                  ue_k TEXT,
                  ue_opc TEXT,
                  tenant_plmn TEXT,
                  tenant_amf_ip TEXT,
                  tenant_amf_port TEXT,
                  accepted TEXT,
                  sc_request_id TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS ues
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  imsi TEXT UNIQUE,
                  k TEXT,
                  opc TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                  
    conn.commit()
    conn.close()
    logging.info("Database initialized.")

def add_ue(imsi, k, opc):
    try:
        conn = sqlite3.connect('requests.db')
        c = conn.cursor()
        c.execute("INSERT INTO ues (imsi, k, opc) VALUES (?, ?, ?)", (imsi, k, opc))
        conn.commit()
        conn.close()
        logging.info(f"UE {imsi} added to database.")
        return True
    except sqlite3.IntegrityError:
        logging.error(f"UE {imsi} already exists.")
        return False
    except Exception as e:
        logging.error(f"Error adding UE: {e}")
        return False

def save_request(request_id, private_key=None, contract_address=None, duration_mins=None, ue_imsi=None, ue_k=None, ue_opc=None, tenant_plmn=None, tenant_amf_ip=None, tenant_amf_port=None, accepted=None, sc_request_id=None):
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
            if duration_mins is not None:
                fields.append("duration_mins = ?")
                values.append(duration_mins)
            if ue_imsi is not None:
                fields.append("ue_imsi = ?")
                values.append(ue_imsi)
            if ue_k is not None:
                fields.append("ue_k = ?")
                values.append(ue_k)
            if ue_opc is not None:
                fields.append("ue_opc = ?")
                values.append(ue_opc)
            if tenant_plmn is not None:
                fields.append("tenant_plmn = ?")
                values.append(tenant_plmn)
            if tenant_amf_ip is not None:
                fields.append("tenant_amf_ip = ?")
                values.append(tenant_amf_ip)
            if tenant_amf_port is not None:
                fields.append("tenant_amf_port = ?")
                values.append(tenant_amf_port)
            if accepted is not None:
                fields.append("accepted = ?")
                values.append(accepted)
            if sc_request_id is not None:
                fields.append("sc_request_id = ?")
                values.append(sc_request_id)
            
            if fields:
                values.append(request_id)
                query = f"UPDATE requests SET {', '.join(fields)} WHERE id = ?"
                c.execute(query, tuple(values))
                logging.info(f"Request {request_id} updated in database.")
            else:
                logging.info(f"Request {request_id} exists, no fields to update.")

        else:
            # Insert new record
            accepted_val = accepted if accepted is not None else 'UNKNOWN'
            c.execute('''INSERT INTO requests 
                         (id, private_key, contract_address, duration_mins, ue_imsi, ue_k, ue_opc, tenant_plmn, tenant_amf_ip, tenant_amf_port, accepted, sc_request_id) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (request_id, private_key, contract_address, duration_mins, ue_imsi, ue_k, ue_opc, tenant_plmn, tenant_amf_ip, tenant_amf_port, accepted_val, sc_request_id))
            logging.info(f"Request {request_id} saved to database.")

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error saving request: {e}")
        return False

def get_request_id_by_sc_id(sc_request_id):
    try:
        conn = sqlite3.connect('requests.db')
        c = conn.cursor()
        c.execute("SELECT id FROM requests WHERE sc_request_id = ?", (sc_request_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return row[0]
        return None
    except Exception as e:
        logging.error(f"Error getting request ID by SC ID: {e}")
        return None
