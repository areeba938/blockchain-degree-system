import sys
import os
from pathlib import Path

from flask import Flask
from config import Config
from my_models import db
from views.routes import init_routes
from controllers.student_controller import student_bp
from controllers import AdminController, BlockchainController
from views.routes import routes

# Ensure current directory and root are in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(str(Path(__file__).parent))


def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config.from_object(Config)
    
    # Initialize database
    db.init_app(app)
    

    # Register routes and blueprints
    init_routes(app)
    app.register_blueprint(student_bp)
    app.register_blueprint(routes)

    # Ensure necessary directories exist
    os.makedirs('data', exist_ok=True)

    # Initialize DB tables and blockchain
    with app.app_context():
        db.create_all()
        AdminController.initialize_admins()
        BlockchainController.initialize_blockchain()

    return app
app = create_app()




if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
