from flask import Flask
import logging
import os
from database import init_db
from routes import api

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Configuration from environment variables with defaults
app.config['NODE_SERVER_URL'] = os.environ.get('NODE_SERVER_URL', 'http://localhost:3020/api')
app.config['AGENT_URL'] = os.environ.get('AGENT_URL', 'http://localhost:28080')

# Initialize Database
init_db()

# Register Blueprint
app.register_blueprint(api)

if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=25000, debug=debug)
