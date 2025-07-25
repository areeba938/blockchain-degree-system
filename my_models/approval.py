from . import db

from datetime import datetime

class Approval(db.Model):
    __tablename__ = 'approvals'
    
    id = db.Column(db.Integer, primary_key=True)
    block_id = db.Column(db.Integer, db.ForeignKey('blockchain.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False)
    approved_at = db.Column(db.DateTime, default=datetime.utcnow)
    approval_status = db.Column(db.Boolean, nullable=False)
    comments = db.Column(db.Text) 
    degree_id = db.Column(db.Integer, db.ForeignKey('degrees.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    def __repr__(self):
        return f'<Approval Block:{self.block_id} Admin:{self.admin_id}>'
