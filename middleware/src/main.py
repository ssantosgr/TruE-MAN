from flask import Flask
import json
import logging
import os
from database import init_db
from routes import api

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Configuration from environment variables with defaults
# app.config['NODE_SERVER_URL'] = os.environ.get('NODE_SERVER_URL', 'https://besu.wimots.com/api')
app.config['NODE_SERVER_URL'] = os.environ.get('NODE_SERVER_URL', 'http://localhost:3020/api')
app.config['AGENT_URL'] = os.environ.get('AGENT_URL', 'http://172.16.100.209:28080')

# Non-tenant agent configuration (gNodeB service parameters)
app.config['AGENT_GNB_ID'] = os.environ.get('AGENT_GNB_ID', '1')
app.config['AGENT_FEATURE_NAME'] = os.environ.get('AGENT_FEATURE_NAME', 'gNodeB_service')

# Non-tenant gNodeB restart parameters
app.config['AGENT_GTP_ADDR'] = os.environ.get('AGENT_GTP_ADDR', '172.16.100.209')
app.config['AGENT_TDD_CONFIG'] = int(os.environ.get('AGENT_TDD_CONFIG', '1'))
app.config['AGENT_AMF_ADDR'] = os.environ.get('AGENT_AMF_ADDR', '172.16.100.202')
app.config['AGENT_NSSAI'] = json.loads(os.environ.get('AGENT_NSSAI', '[{"sst":1}, {"sst": 1, "sd":10}, {"sst":1, "sd":11}, {"sst":1, "sd":12}]'))
app.config['AGENT_PLMN'] = os.environ.get('AGENT_PLMN', '99940')
app.config['AGENT_TAC'] = int(os.environ.get('AGENT_TAC', '100'))

# Initialize Database
init_db()

# Register Blueprint
app.register_blueprint(api)

if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=25000, debug=debug)
