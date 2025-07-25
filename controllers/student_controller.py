from flask import Blueprint, render_template, request, redirect, session, url_for, flash, send_file
from my_models import db, Student
from my_models.degree import Degree
from werkzeug.security import generate_password_hash, check_password_hash
from utils.certificate_pdf import generate_pdf
from my_models.approval import Approval
from utils.blockchain_utils import is_certificate_on_blockchain
student_bp = Blueprint('student', __name__)
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# -------- Student Account Management -------- #


class StudentController:
    @staticmethod
    def create_student(student_id, full_name, email, password):
        # Validate required fields
        if not student_id or not full_name or not email or not password:
            return False, "All fields are required."

        # Check if student already exists
        if Student.query.filter_by(student_id=student_id).first():
            return False, "Student already exists."

        # Create student object
        new_student = Student(
            student_id=student_id,
            full_name=full_name,
            email=email
        )

        # Set password hash
        new_student.set_password(password)

        try:
            # Save to DB
            db.session.add(new_student)
            db.session.commit()
            return True, "Student created successfully."
        except Exception as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"

    
    @staticmethod
    def get_student(student_id):
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            return False, "Student not found"
        return True, student

# -------- Authentication Routes -------- #

@student_bp.route('/student/login', methods=['GET', 'POST'])
def login_student():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        password = request.form.get('password')

        if not (student_id and password):
            flash('Please fill out all fields')
            return render_template('student/login.html')

        student = Student.query.filter_by(student_id=student_id).first()
        if student and check_password_hash(student.password_hash, password):
            session['student_id'] = student.student_id
            return redirect(url_for('student.dashboard'))

        flash('Invalid credentials')
    return render_template('student/login.html')


@student_bp.route('/student/logout')
def logout_student():
    session.pop('student_id', None)
    return redirect(url_for('student.login_student'))

# -------- Dashboard Route -------- #

# --- inside student_controller.py ---

@student_bp.route('/student/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('student.login_student'))

    student_id = session['student_id']
    student_obj = Student.query.filter_by(student_id=student_id).first()
    cert_objs = Degree.query.filter_by(student_id=student_id).all()

    certificates = []
    for cert in cert_objs:
        # Check if approved by all 3 admins
        approvals = Approval.query.filter_by(degree_id=cert.id, approval_status=True).count()

        is_on_chain = is_certificate_on_blockchain(cert.id)  # You need to implement this function

        if approvals == 3 and is_on_chain and cert.status != 'approved':
            cert.status = 'approved'
            db.session.commit()

        certificates.append((cert.id, cert.status, cert.status == 'approved'))

    student = [student_obj.full_name, student_obj.student_id, student_obj.email]

    return render_template('student/dashboard.html', student=student, certificates=certificates)


# -------- PDF Download (Conditional) -------- #

@student_bp.route('/student/download_certificate/<int:degree_id>')
def download_certificate(degree_id):
    if 'student_id' not in session:
        return redirect(url_for('student.login_student'))

    student_id = session['student_id']
    degree = Degree.query.filter_by(id=degree_id, student_id=student_id).first()
    if not degree:
        return "Certificate not found or not approved.", 403

    pdf_path = generate_pdf(degree)  # your existing PDF logic
    return send_file(pdf_path, as_attachment=True)


# -------- Admin Add Student Route -------- #

@student_bp.route('/admin/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        default_password = '123456'  # You can replace this with a more secure password

        if not student_id or not full_name or not email:
            flash("All fields are required", 'error')
            return redirect(url_for('student.add_student'))

        # Create student using the controller
        success, message = StudentController.create_student(
            student_id=student_id,
            full_name=full_name,
            email=email,
            password=default_password
        )

        if success:
            # Log the student in by storing session
            session['student_id'] = student_id

            # Optional flash message
            flash('Student registered and logged in. You can now request a degree.', 'success')

            # Redirect to degree add page
            return redirect(url_for('add_degree'))
        else:
            flash(f"Failed: {message}", 'error')
            return redirect(url_for('student.add_student'))

    return render_template('admin/add_student.html')