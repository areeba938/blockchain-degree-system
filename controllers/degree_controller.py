from my_models import db, Degree, Student
from datetime import datetime

# Rest of the file remains the same
from datetime import datetime

# controllers/degree_controller.py
class DegreeController:
    @staticmethod
    def add_degree(student_id, degree_name, institution, year_awarded, field_of_study):
        # Check if student exists
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            return False, "Student not found", None
        
        # Create new degree
        new_degree = Degree(
            student_id=student_id,
            degree_name=degree_name,
            institution=institution,
            year_awarded=year_awarded,
            field_of_study=field_of_study
        )
        
        try:
            db.session.add(new_degree)
            db.session.commit()
            return True, "Degree added successfully", new_degree.id
        except Exception as e:
            db.session.rollback()
            return False, f"Error adding degree: {str(e)}", None
    
    @staticmethod
    def get_degree(degree_id):
        degree = Degree.query.get(degree_id)
        if not degree:
            return False, "Degree not found"
        
        return True, degree
    
    @staticmethod
    def get_all_degrees():
        degrees = Degree.query.all()
        return degrees
    
    @staticmethod
    def get_student_degrees(student_id):
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            return False, "Student not found"
        
        degrees = Degree.query.filter_by(student_id=student_id).all()
        return True, degrees
    
    @staticmethod
    def get_degree_with_blockchain(degree_id):
        from my_models import Block
        degree = Degree.query.get(degree_id)
        if not degree:
            return False, "Degree not found"
        
        block = Block.query.filter_by(degree_id=degree_id).first()
        return True, degree, block