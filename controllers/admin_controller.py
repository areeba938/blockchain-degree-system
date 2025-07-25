from my_models import db, Admin
from utils.crypto import generate_key_pair
from werkzeug.security import generate_password_hash

class AdminController:
    @staticmethod
    def initialize_admins():
        # Check if any admins exist
        if Admin.query.count() > 0:
            return False, "Admins already initialized"
        
        # Create 3 admins
        for i in range(1, 4):
            private_key, public_key = generate_key_pair()
            
            admin = Admin(
                username=f'admin{i}',
                public_key=public_key.decode()
            )
            admin.set_password(f'admin{i}password')
            
            db.session.add(admin)
        
        db.session.commit()
        return True, "Admins initialized successfully"
    
    @staticmethod
    def authenticate(username, password):
        admin = Admin.query.filter_by(username=username).first()
        if not admin or not admin.check_password(password):
            return False, "Invalid credentials"
        
        return True, admin
    
    @staticmethod
    def get_admin(admin_id):
        admin = Admin.query.get(admin_id)
        if not admin:
            return False, "Admin not found"
        
        return True, admin
    
    @staticmethod
    def get_pending_approvals():
        from my_models import Block
        return Block.query.filter_by(approved=False).order_by(Block.timestamp.desc()).all()
    
    @staticmethod
    def get_admin_approvals(admin_id):
        from my_models import Approval
        return Approval.query.filter_by(admin_id=admin_id).all()