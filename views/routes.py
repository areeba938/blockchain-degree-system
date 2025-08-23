import os
from flask import render_template, request, redirect, url_for, session, jsonify, flash, send_file, Blueprint
from my_models import db, Student, Degree, Block, Admin, Approval
from controllers.admin_controller import AdminController
from controllers.student_controller import StudentController 
from controllers.degree_controller import DegreeController
from controllers.blockchain_controller import BlockchainController
from datetime import datetime
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


routes = Blueprint('routes', __name__)

def init_routes(app):
    @app.route('/')
    def home():
        return render_template('public/verify.html')

    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            VALID_ADMIN_USERNAMES = ['admin1', 'admin2', 'admin3']

            if username not in VALID_ADMIN_USERNAMES:
                
                flash('Unauthorized admin username.', 'error')
                return render_template('admin/login.html')

            success, result = AdminController.authenticate(username, password)

            if not success:
                flash(result, 'error')
                return render_template('admin/login.html')
            
            session['admin_id'] = result.id
            session['admin_username'] = result.username
            return redirect(url_for('admin_dashboard'))
        
        return render_template('admin/login.html')

    @app.route('/admin/logout')
    def admin_logout():
        session.pop('admin_id', None)
        session.pop('admin_username', None)
        return redirect(url_for('home'))

    @app.route('/admin/dashboard')
    def admin_dashboard():
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        
        pending_blocks = AdminController.get_pending_approvals()
        admin_approvals = AdminController.get_admin_approvals(session['admin_id'])
        approved_block_ids = [a.block_id for a in admin_approvals if a.approval_status]

        pending_student_ids = list({block.degree.student_id for block in pending_blocks})
        pending_students = Student.query.filter(Student.student_id.in_(pending_student_ids)).all()
        
        return render_template(
            'admin/dashboard.html',
            pending_blocks=pending_blocks,
            admin_approvals=admin_approvals,
            approved_block_ids=approved_block_ids,
            pending_students=pending_students
        )

    @app.route('/admin/approve/<int:block_id>', methods=['POST'])
    def approve_block(block_id):
        if 'admin_id' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401

        try:
            success, message = BlockchainController.approve_block(block_id, session['admin_id'])
            return jsonify({'success': success, 'message': message})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/student/add', methods=['GET', 'POST'])
    def add_student():
        if request.method == 'POST':
            student_id = request.form.get('student_id')
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            
            default_password = "default_password_123"
            success, message = StudentController.create_student(
                student_id=student_id,
                full_name=full_name,
                email=email,
                password=default_password
            )
            flash(message, 'success' if success else 'error')
            if success:
                return redirect(url_for('add_degree'))

        return render_template('admin/add_student.html')

    @app.route('/degree/add', methods=['GET', 'POST'])
    def add_degree():
        if request.method == 'POST':
            student_id = request.form.get('student_id')
            degree_name = request.form.get('degree_name')
            institution = request.form.get('institution')
            year_awarded = request.form.get('year_awarded')
            field_of_study = request.form.get('field_of_study')

        # 🔒 1. Check if same degree already exists (duplicate check)
            duplicate = Degree.query.filter_by(
                student_id=student_id,
                degree_name=degree_name,
                institution=institution,
                year_awarded=year_awarded,
                field_of_study=field_of_study
            ).first()

            if duplicate:
                flash("This exact degree has already been submitted. Please edit or wait for approval.", 'warning')
                return redirect(url_for('add_degree'))
            existing_count = Degree.query.filter_by(student_id=student_id).count()
            if existing_count >= 3:
                flash("You’ve already submitted 2 degree requests. No further submissions allowed.", "error")
                return redirect(url_for('add_degree'))


        # ✅ 3. Add new degree now
            success, message, degree_id = DegreeController.add_degree(
                student_id, degree_name, institution, year_awarded, field_of_study
            )

            if not success or not degree_id:
                flash(message, 'error')
                return render_template('student/add_degree.html')

        # ✅ 4. Add to blockchain
            success, msg = BlockchainController.add_degree_to_blockchain(degree_id)
            if not success:
                flash(f"Blockchain error: {msg}", 'error')
                return redirect(url_for('add_degree'))

            flash("Degree added successfully! Waiting for admin approvals.", 'success')
            return redirect(url_for('view_degree', degree_id=degree_id))

        return render_template('student/add_degree.html')
    @app.route('/degree/<int:degree_id>')
    def view_degree(degree_id):
        success, degree, block = DegreeController.get_degree_with_blockchain(degree_id)
        if not success:
            flash(degree, 'error')
            return redirect(url_for('home'))
        
        approvals = []
        if block:
            approvals = Approval.query.filter_by(block_id=block.id).all()
        
        return render_template(
            'student/view_degree.html',
            degree=degree,
            block=block,
            approvals=approvals
        )

    @app.route('/verify', methods=['GET', 'POST']) 
    def verify_degree():
        if request.method == 'POST':
            identifier = request.form.get('degree_id', '').strip()
            success, result = BlockchainController.verify_degree(identifier)

            if success:
                flash("Degree verified successfully!", 'success')
                return render_template('public/verify.html', verification_result=result, verified=True)
            else:
                flash(result, 'error')
                return redirect(url_for('home'))

        return render_template('public/verify.html')


    @app.route('/blockchain')
    def view_blockchain():
        blockchain = BlockchainController.get_blockchain()
        blocks = BlockchainController.get_blockchain_blocks()
        print("DEBUG blockchain data:", blockchain)
        return render_template('public/blockchain.html', blockchain=blockchain, blocks=blocks)

    @app.route('/admin/approval/<int:block_id>')
    def approval_details(block_id):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        
        block = Block.query.get(block_id)
        if not block:
            return render_template('admin/approval.html')
        
        approvals = Approval.query.filter_by(block_id=block_id).all()
        current_user_approval = Approval.query.filter_by(
            block_id=block_id,
            admin_id=session['admin_id']
        ).first()
        
        return render_template(
            'admin/approval.html',
            block=block,
            approvals=approvals,
            current_user_approval=current_user_approval
        )

    @app.route('/admin/approval/<int:block_id>/process', methods=['POST'])
    def process_approval(block_id):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))

        block = Block.query.get(block_id)
        if not block:
            flash('Block not found', 'error')
            return redirect(url_for('admin_dashboard'))

        if block.approved:
            flash('This degree has already been approved', 'warning')
            return redirect(url_for('approval_details', block_id=block_id))

        existing_approval = Approval.query.filter_by(
            block_id=block_id,
            admin_id=session['admin_id']
        ).first()

        if existing_approval:
            flash('You have already submitted an approval for this degree', 'warning')
            return redirect(url_for('approval_details', block_id=block_id))

        approval_status = request.form.get('approval_status') == 'approve'
        comments = request.form.get('comments', '')

        new_approval = Approval(
            block_id=block_id,
            admin_id=session['admin_id'],
            degree_id=block.degree_id,
            approval_status=approval_status,
            comments=comments
        )

        db.session.add(new_approval)

        approval_count = Approval.query.filter_by(
            block_id=block_id,
            approval_status=True
        ).count()

        if approval_count == 3:
            block.approved = True
            degree = Degree.query.get(block.degree_id)
            if degree:
                degree.status = 'Approved'
                db.session.add(degree)
                db.session.add(block)  
                db.session.commit() 
            BlockchainController._add_to_json_blockchain(block)
            flash('Degree has been fully approved and added to the blockchain!', 'success')
        else:
            db.session.commit()    
            flash('Your approval has been recorded', 'success')

        return redirect(url_for('approval_details', block_id=block_id))

    @app.route('/download_certificate/<int:degree_id>')
    def download_certificate(degree_id):
        # Ensure the student is logged in
        if 'student_id' not in session:
            flash('You must be logged in to download your certificate.', 'warning')
            return redirect(url_for('student_login'))

        degree = Degree.query.get(degree_id)
        if not degree:
            flash('Degree not found', 'danger')
            return redirect(url_for('student_dashboard'))

         # Ensure the degree belongs to the logged-in student
        if degree.student_id != session['student_id']:
            flash('Unauthorized access to this certificate.', 'danger')
            return redirect(url_for('student_dashboard'))

        if degree.status != 'Approved':
            flash('Certificate not generated yet. Degree is not approved.', 'warning')
            return redirect(url_for('student_dashboard'))

        student = Student.query.filter_by(student_id=degree.student_id).first()
        if not student:
            flash('Student details not found', 'danger')
            return redirect(url_for('student_dashboard'))

        # Generate the in-memory PDF
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        p.setFont("Helvetica", 18)
        p.drawString(100, 700, "University of Kashmir Main Campus")
        p.setFont("Helvetica", 14)
        p.drawString(100, 660, "Degree Certificate")
        p.drawString(100, 630, f"Student Name: {student.name}")
        p.drawString(100, 610, f"Student ID: {student.student_id}")
        p.drawString(100, 590, f"Degree Name: {degree.degree_name}")
        p.drawString(100, 570, f"Year Awarded: {degree.year_awarded}")
        p.drawString(100, 550, f"Field of Study: {degree.field_of_study}")
        p.drawString(100, 530, f"Institution: {degree.institution}")
        p.drawString(100, 500, f"Status: {degree.status}")
        p.showPage()
        p.save()
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"certificate_{degree_id}.pdf",
            mimetype='application/pdf'
    )

    @app.context_processor
    def inject_now():
        return {'now': datetime.now}