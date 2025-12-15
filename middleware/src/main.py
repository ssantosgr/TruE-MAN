from flask import Flask
import logging
from database import init_db
from routes import api

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config['NODE_SERVER_URL'] = "http://localhost:3020/api"

# Initialize Database
init_db()

# Register Blueprint
app.register_blueprint(api)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
