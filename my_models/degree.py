from . import db

from datetime import datetime

def utcnow_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat()


class Degree(db.Model):
    __tablename__ = 'degrees'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), db.ForeignKey('students.student_id'), nullable=False)
    degree_name = db.Column(db.String(100), nullable=False)
    institution = db.Column(db.String(100), nullable=False)
    year_awarded = db.Column(db.Integer, nullable=False)
    field_of_study = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow_iso)
    status = db.Column(db.String(20), default='Pending')
    blockchain_entry = db.relationship('Block', backref='degree', uselist=False, lazy=True)
    approvals = db.relationship('Approval', backref='degree', lazy=True)

    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'degree_name': self.degree_name,
            'institution': self.institution,
            'year_awarded': self.year_awarded,
            'field_of_study': self.field_of_study,
            'created_at': self.created_at
        }
    @property
    def approved_by(self):
        approvers = []
        for approval in self.approvals:
            if approval.status == 'approved':
                approvers.append(approval.admin.role.capitalize())
        return ", ".join(approvers) if approvers else "Not Approved"
    
    def __repr__(self):
        return f'<Degree {self.degree_name} - {self.student_id}>'