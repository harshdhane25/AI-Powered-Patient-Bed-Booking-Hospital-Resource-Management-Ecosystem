# app.py (Full updated code with new changes)

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, send_file, make_response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os
import json
import razorpay
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['RAZORPAY_KEY_ID'] = 'rzp_test_RPURGWwDtViv9P'  # Enter your Razorpay key here
app.config['RAZORPAY_KEY_SECRET'] = 'gHB7AScqU12PUikgM7Fibsu3'  # Enter your Razorpay secret here
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SENDER_EMAIL'] = 'harshvardhandhane13@gmail.com'
app.config['SENDER_PASSWORD'] = 'ipde veha zmzs hhlb'
db = SQLAlchemy(app)
razorpay_client = razorpay.Client(auth=(app.config['RAZORPAY_KEY_ID'], app.config['RAZORPAY_KEY_SECRET']))

def send_email(to_email, subject, body, pdf_buffer=None):
    msg = MIMEMultipart()
    msg['From'] = app.config['SENDER_EMAIL']
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    if pdf_buffer:
        pdf_buffer.seek(0)
        attach = MIMEApplication(pdf_buffer.getvalue(), _subtype='pdf')
        attach.add_header('Content-Disposition', 'attachment', filename='bill.pdf')
        msg.attach(attach)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(app.config['SENDER_EMAIL'], app.config['SENDER_PASSWORD'])
        text = msg.as_string()
        server.sendmail(app.config['SENDER_EMAIL'], to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False

def generate_booking_bill_pdf(booking, bed, room):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Hospital Bill")
    y = 700
    p.drawString(100, y, f"Patient Name: {booking.patient_name}")
    y -= 20
    p.drawString(100, y, f"Age: {booking.age}")
    y -= 20
    p.drawString(100, y, f"Contact: {booking.contact_number}")
    y -= 20
    p.drawString(100, y, f"Check-in Date: {booking.check_in_date}")
    y -= 20
    p.drawString(100, y, f"Estimated Stay: {booking.estimated_stay} days")
    y -= 20
    p.drawString(100, y, f"Room: {room.name}")
    y -= 20
    p.drawString(100, y, f"Bed: {bed.bed_number}")
    y -= 20
    p.drawString(100, y, f"Price per day: ${room.price_per_bed}")
    y -= 20
    p.drawString(100, y, f"Total Amount: ${room.price_per_bed * booking.estimated_stay}")
    p.save()
    return buffer

def generate_appointment_bill_pdf(appointment, time_slot):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Appointment Bill")
    y = 700
    p.drawString(100, y, f"Patient Name: {appointment.patient.name}")
    y -= 20
    p.drawString(100, y, f"Doctor Name: {appointment.doctor.name}")
    y -= 20
    p.drawString(100, y, f"Appointment Date: {appointment.appointment_date}")
    y -= 20
    p.drawString(100, y, f"Time Slot: {time_slot.start_time} - {time_slot.end_time}")
    y -= 20
    p.drawString(100, y, f"Amount: ${time_slot.price}")
    p.save()
    return buffer

def generate_ambulance_bill_pdf(booking, vehicle):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Ambulance Bill")
    y = 700
    p.drawString(100, y, f"Patient Name: {booking.patient.name}")
    y -= 20
    p.drawString(100, y, f"Vehicle: {vehicle.name}")
    y -= 20
    p.drawString(100, y, f"Numberplate: {vehicle.numberplate}")
    y -= 20
    p.drawString(100, y, f"Use Type: {booking.use_type}")
    if booking.location_link:
        y -= 20
        p.drawString(100, y, f"Location Link: {booking.location_link}")
    y -= 20
    p.drawString(100, y, f"Amount: ${booking.amount}")
    p.save()
    return buffer

# Models
class Hospital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    info= db.Column(db.Text, nullable=True)

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    info = db.Column(db.Text, nullable=True)  # Professional Information
    qualifications = db.Column(db.Text, nullable=True)
    specializations = db.Column(db.Text, nullable=True)
    practice_years = db.Column(db.Integer, nullable=True)
    additional_links = db.Column(db.Text, nullable=True)
    practice_location = db.Column(db.String(255), nullable=True)
    time_slots = db.relationship('TimeSlot', backref='doctor', lazy=True, cascade="all, delete-orphan")
    medical_records = db.relationship('MedicalRecord', backref='doctor', lazy=True, cascade="all, delete-orphan")
    appointments = db.relationship('Appointment', backref='doctor', lazy=True, cascade="all, delete-orphan")
    doctor_reviews = db.relationship('DoctorReview', backref='doctor', lazy=True, cascade="all, delete-orphan")

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    start_time = db.Column(db.String(5), nullable=False)  # e.g., '09:00'
    end_time = db.Column(db.String(5), nullable=False)    # e.g., '10:00'
    price = db.Column(db.Float, nullable=False)
    appointments = db.relationship('Appointment', backref='time_slot', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    medical_condition = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Ambulance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    info = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='available')  # available, on duty, under maintenance
    vehicles = db.relationship('AmbulanceVehicle', backref='ambulance', lazy=True, cascade="all, delete-orphan")
    bookings = db.relationship('AmbulanceBooking', backref='ambulance', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('AmbulanceReview', backref='ambulance', lazy=True, cascade="all, delete-orphan")

class AmbulanceVehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ambulance_id = db.Column(db.Integer, db.ForeignKey('ambulance.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    numberplate = db.Column(db.String(50), nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    medical_support = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    bookings = db.relationship('AmbulanceBooking', backref='vehicle', lazy=True)

class AmbulanceBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ambulance_id = db.Column(db.Integer, db.ForeignKey('ambulance.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('ambulance_vehicle.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    use_type = db.Column(db.String(20), nullable=False)  # emergency or normal
    location_link = db.Column(db.Text, nullable=True)  # patient's for emergency, ambulance's for normal
    live_location_link = db.Column(db.Text, nullable=True)  # ambulance's live link for normal
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AmbulanceReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ambulance_id = db.Column(db.Integer, db.ForeignKey('ambulance.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Nurse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    info = db.Column(db.Text, nullable=True)

class Canteen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    info = db.Column(db.Text, nullable=True)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    info = db.Column(db.Text, nullable=True)
    appointments = db.relationship('Appointment', backref='patient', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='patient', lazy=True, cascade="all, delete-orphan")
    doctor_reviews = db.relationship('DoctorReview', backref='patient', lazy=True, cascade="all, delete-orphan")
    ambulance_bookings = db.relationship('AmbulanceBooking', backref='patient', lazy=True, cascade="all, delete-orphan")
    ambulance_reviews = db.relationship('AmbulanceReview', backref='patient', lazy=True, cascade="all, delete-orphan")

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    num_beds = db.Column(db.Integer, nullable=False)
    price_per_bed = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    beds = db.relationship('Bed', backref='room', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='room', lazy=True, cascade="all, delete-orphan")

class Bed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    bed_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='available')
    position = db.Column(db.String(50), nullable=True)
    bookings = db.relationship('Booking', backref='bed', lazy=True, cascade="all, delete-orphan")

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bed_id = db.Column(db.Integer, db.ForeignKey('bed.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    patient_name = db.Column(db.String(100))
    contact_number = db.Column(db.String(20))
    age = db.Column(db.Integer)
    medical_condition = db.Column(db.Text)
    estimated_stay = db.Column(db.Integer)
    check_in_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DoctorReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create database
with app.app_context():
    db.create_all()

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Routes (all existing + new)
@app.route('/')
def index():
    return render_template('index.html')

# Hospital Admin Routes (unchanged)
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hospital = Hospital.query.filter_by(username=username).first()
        if hospital and check_password_hash(hospital.password, password):
            session['user_id'] = hospital.id
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        flash('Invalid username or password')
    return render_template('admin_login.html')

@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('admin_register.html')
        if Hospital.query.filter_by(username=username).first() or Hospital.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return render_template('admin_register.html')
        hashed_password = generate_password_hash(password)
        new_hospital = Hospital(name=name, username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_hospital)
        db.session.commit()
        return redirect(url_for('admin_login'))
    return render_template('admin_register.html')

@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    hospital = Hospital.query.get(session['user_id'])
    if request.method == 'POST' and 'edit' in request.form:
        hospital.name = request.form['name']
        hospital.mobile = request.form['mobile']
        hospital.email = request.form['email']
        hospital.info = request.form['info']
        db.session.commit()
        flash('Details updated')
    return render_template('admin_dashboard.html', hospital=hospital)

@app.route('/admin/doctors', methods=['GET', 'POST'])
def admin_doctors():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    hospital_id = session['user_id']
    doctors = Doctor.query.filter_by(hospital_id=hospital_id).all()
    if request.method == 'POST' and 'add' in request.form:
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('admin_doctors.html', doctors=doctors)
        if Doctor.query.filter_by(username=username).first() or Doctor.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return render_template('admin_doctors.html', doctors=doctors)
        hashed_password = generate_password_hash(password)
        new_doctor = Doctor(hospital_id=hospital_id, name=name, username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_doctor)
        db.session.commit()
        flash('Doctor added')
        return redirect(url_for('admin_doctors'))
    return render_template('admin_doctors.html', doctors=doctors)

@app.route('/admin/doctors/edit/<int:doctor_id>', methods=['GET', 'POST'])
def admin_edit_doctor(doctor_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    if doctor.hospital_id != session['user_id']:
        return redirect(url_for('admin_doctors'))
    if request.method == 'POST':
        doctor.name = request.form['name']
        doctor.mobile = request.form['mobile']
        doctor.email = request.form['email']
        db.session.commit()
        flash('Doctor updated')
        return redirect(url_for('admin_doctors'))
    return render_template('admin_edit_doctor.html', doctor=doctor)

@app.route('/admin/doctors/remove/<int:doctor_id>')
def admin_remove_doctor(doctor_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    if doctor.hospital_id != session['user_id']:
        return redirect(url_for('admin_doctors'))
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor removed')
    return redirect(url_for('admin_doctors'))

# Ambulance Admin Routes (unchanged)
@app.route('/admin/ambulances', methods=['GET', 'POST'])
def admin_ambulances():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    hospital_id = session['user_id']
    ambulances = Ambulance.query.filter_by(hospital_id=hospital_id).all()
    if request.method == 'POST' and 'add' in request.form:
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('admin_ambulances.html', ambulances=ambulances)
        if Ambulance.query.filter_by(username=username).first() or Ambulance.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return render_template('admin_ambulances.html', ambulances=ambulances)
        hashed_password = generate_password_hash(password)
        new_ambulance = Ambulance(hospital_id=hospital_id, name=name, username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_ambulance)
        db.session.commit()
        flash('Ambulance added')
        return redirect(url_for('admin_ambulances'))
    return render_template('admin_ambulances.html', ambulances=ambulances)

@app.route('/admin/ambulances/edit/<int:ambulance_id>', methods=['GET', 'POST'])
def admin_edit_ambulance(ambulance_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    ambulance = Ambulance.query.get_or_404(ambulance_id)
    if ambulance.hospital_id != session['user_id']:
        return redirect(url_for('admin_ambulances'))
    if request.method == 'POST':
        ambulance.name = request.form['name']
        ambulance.mobile = request.form['mobile']
        ambulance.email = request.form['email']
        db.session.commit()
        flash('Ambulance updated')
        return redirect(url_for('admin_ambulances'))
    return render_template('admin_edit_ambulance.html', ambulance=ambulance)

@app.route('/admin/ambulances/remove/<int:ambulance_id>')
def admin_remove_ambulance(ambulance_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    ambulance = Ambulance.query.get_or_404(ambulance_id)
    if ambulance.hospital_id != session['user_id']:
        return redirect(url_for('admin_ambulances'))
    db.session.delete(ambulance)
    db.session.commit()
    flash('Ambulance removed')
    return redirect(url_for('admin_ambulances'))

# Nurse (unchanged)
@app.route('/admin/nurses', methods=['GET', 'POST'])
def admin_nurses():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    hospital_id = session['user_id']
    nurses = Nurse.query.filter_by(hospital_id=hospital_id).all()
    if request.method == 'POST' and 'add' in request.form:
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('admin_nurses.html', nurses=nurses)
        if Nurse.query.filter_by(username=username).first() or Nurse.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return render_template('admin_nurses.html', nurses=nurses)
        hashed_password = generate_password_hash(password)
        new_nurse = Nurse(hospital_id=hospital_id, name=name, username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_nurse)
        db.session.commit()
        flash('Nurse added')
        return redirect(url_for('admin_nurses'))
    return render_template('admin_nurses.html', nurses=nurses)

@app.route('/admin/nurses/edit/<int:nurse_id>', methods=['GET', 'POST'])
def admin_edit_nurse(nurse_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    nurse = Nurse.query.get_or_404(nurse_id)
    if nurse.hospital_id != session['user_id']:
        return redirect(url_for('admin_nurses'))
    if request.method == 'POST':
        nurse.name = request.form['name']
        nurse.mobile = request.form['mobile']
        nurse.email = request.form['email']
        db.session.commit()
        flash('Nurse updated')
        return redirect(url_for('admin_nurses'))
    return render_template('admin_edit_nurse.html', nurse=nurse)

@app.route('/admin/nurses/remove/<int:nurse_id>')
def admin_remove_nurse(nurse_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    nurse = Nurse.query.get_or_404(nurse_id)
    if nurse.hospital_id != session['user_id']:
        return redirect(url_for('admin_nurses'))
    db.session.delete(nurse)
    db.session.commit()
    flash('Nurse removed')
    return redirect(url_for('admin_nurses'))

# Canteen (unchanged)
@app.route('/admin/canteens', methods=['GET', 'POST'])
def admin_canteens():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    hospital_id = session['user_id']
    canteens = Canteen.query.filter_by(hospital_id=hospital_id).all()
    if request.method == 'POST' and 'add' in request.form:
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('admin_canteens.html', canteens=canteens)
        if Canteen.query.filter_by(username=username).first() or Canteen.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return render_template('admin_canteens.html', canteens=canteens)
        hashed_password = generate_password_hash(password)
        new_canteen = Canteen(hospital_id=hospital_id, name=name, username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_canteen)
        db.session.commit()
        flash('Canteen added')
        return redirect(url_for('admin_canteens'))
    return render_template('admin_canteens.html', canteens=canteens)

@app.route('/admin/canteens/edit/<int:canteen_id>', methods=['GET', 'POST'])
def admin_edit_canteen(canteen_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    canteen = Canteen.query.get_or_404(canteen_id)
    if canteen.hospital_id != session['user_id']:
        return redirect(url_for('admin_canteens'))
    if request.method == 'POST':
        canteen.name = request.form['name']
        canteen.mobile = request.form['mobile']
        canteen.email = request.form['email']
        db.session.commit()
        flash('Canteen updated')
        return redirect(url_for('admin_canteens'))
    return render_template('admin_edit_canteen.html', canteen=canteen)

@app.route('/admin/canteens/remove/<int:canteen_id>')
def admin_remove_canteen(canteen_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    canteen = Canteen.query.get_or_404(canteen_id)
    if canteen.hospital_id != session['user_id']:
        return redirect(url_for('admin_canteens'))
    db.session.delete(canteen)
    db.session.commit()
    flash('Canteen removed')
    return redirect(url_for('admin_canteens'))

# Admin Rooms Management (unchanged)
@app.route('/admin/rooms', methods=['GET', 'POST'])
def admin_rooms():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    hospital_id = session['user_id']
    rooms = Room.query.filter_by(hospital_id=hospital_id).all()
    bookings = Booking.query.join(Bed).join(Room).filter(Room.hospital_id == hospital_id).all()
    active_bookings = [b for b in bookings if b.status == 'pending']
    history_bookings = [b for b in bookings if b.status in ['accepted', 'rejected', 'cancelled']]
    confirmed_bookings = [b for b in bookings if b.status == 'paid']
    if request.method == 'POST' and 'create_room' in request.form:
        name = request.form['name']
        num_beds = int(request.form['num_beds'])
        price_per_bed = float(request.form['price_per_bed'])
        description = request.form.get('description')
        layout_json = request.form['layout']
        layout = json.loads(layout_json)
        new_room = Room(hospital_id=hospital_id, name=name, num_beds=num_beds, price_per_bed=price_per_bed, description=description)
        db.session.add(new_room)
        db.session.commit()
        for item in layout:
            bed = Bed(room_id=new_room.id, bed_number=item['number'], position=f"{item['left']},{item['top']}")
            db.session.add(bed)
        db.session.commit()
        flash('Room created')
        return redirect(url_for('admin_rooms'))
    return render_template('admin_rooms.html', rooms=rooms, active_bookings=active_bookings, history_bookings=history_bookings, confirmed_bookings=confirmed_bookings)

@app.route('/admin/rooms/edit/<int:room_id>', methods=['GET', 'POST'])
def admin_edit_room(room_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    room = Room.query.get_or_404(room_id)
    if room.hospital_id != session['user_id']:
        abort(403)
    reviews = Review.query.filter_by(room_id=room_id).order_by(Review.created_at.desc()).all()
    if request.method == 'POST':
        room.name = request.form['name']
        room.price_per_bed = float(request.form['price_per_bed'])
        room.description = request.form.get('description')
        layout_json = request.form['layout']
        layout = json.loads(layout_json)
        beds = Bed.query.filter_by(room_id=room_id).order_by(Bed.bed_number).all()
        for i, item in enumerate(layout):
            beds[i].position = f"{item['left']},{item['top']}"
        db.session.commit()
        flash('Room updated')
        return redirect(url_for('admin_rooms'))
    beds = Bed.query.filter_by(room_id=room_id).order_by(Bed.bed_number).all()
    initial_layout = []
    for bed in beds:
        left, top = bed.position.split(',') if bed.position else ('0px', '0px')
        initial_layout.append({'id': bed.id, 'number': bed.bed_number, 'status': bed.status, 'left': left, 'top': top})
    return render_template('admin_edit_room.html', room=room, initial_layout=json.dumps(initial_layout), reviews=reviews)

@app.route('/admin/rooms/delete/<int:room_id>')
def admin_delete_room(room_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    room = Room.query.get_or_404(room_id)
    if room.hospital_id != session['user_id']:
        abort(403)
    db.session.delete(room)
    db.session.commit()
    flash('Room deleted')
    return redirect(url_for('admin_rooms'))

@app.route('/admin/accept_booking/<int:booking_id>')
def admin_accept_booking(booking_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    booking = Booking.query.get_or_404(booking_id)
    bed = Bed.query.get(booking.bed_id)
    room = Room.query.get(bed.room_id)
    if room.hospital_id != session['user_id']:
        abort(403)
    booking.status = 'accepted'
    db.session.commit()
    flash('Booking accepted')
    # Send email to patient
    patient = Patient.query.get(booking.patient_id)
    if patient and patient.email:
        subject = "Bed Booking Request Accepted"
        body = f"Dear {patient.name},\n\nYour bed booking request has been accepted. Please pay the bill to confirm.\n\nBest regards,\nHospital Team"
        send_email(patient.email, subject, body)
    return redirect(url_for('admin_rooms'))

@app.route('/admin/reject_booking/<int:booking_id>')
def admin_reject_booking(booking_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    booking = Booking.query.get_or_404(booking_id)
    bed = Bed.query.get(booking.bed_id)
    room = Room.query.get(bed.room_id)
    if room.hospital_id != session['user_id']:
        abort(403)
    booking.status = 'rejected'
    db.session.commit()
    flash('Booking rejected')
    # Send email to patient
    patient = Patient.query.get(booking.patient_id)
    if patient and patient.email:
        subject = "Bed Booking Request Rejected"
        body = f"Dear {patient.name},\n\nYour bed booking request has been rejected.\n\nBest regards,\nHospital Team"
        send_email(patient.email, subject, body)
    return redirect(url_for('admin_rooms'))

@app.route('/admin/room/<int:room_id>/unbook_bed/<int:bed_id>')
def admin_unbook_bed(room_id, bed_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    bed = Bed.query.get_or_404(bed_id)
    if bed.room_id != room_id:
        abort(404)
    room = Room.query.get(room_id)
    if room.hospital_id != session['user_id']:
        abort(403)
    if bed.status == 'booked':
        booking = Booking.query.filter_by(bed_id=bed_id, status='paid').first()
        if booking:
            booking.status = 'cancelled'
            # Send email to patient for cancellation
            patient = Patient.query.get(booking.patient_id)
            if patient and patient.email:
                subject = "Bed Booking Cancelled"
                body = f"Dear {patient.name},\n\nYour bed booking has been cancelled by admin.\n\nBest regards,\nHospital Team"
                send_email(patient.email, subject, body)
        bed.status = 'available'
        db.session.commit()
        flash('Bed unbooked')
    return redirect(url_for('admin_edit_room', room_id=room_id))

@app.route('/admin/delete_review/<int:review_id>')
def admin_delete_review(review_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    review = Review.query.get_or_404(review_id)
    room = review.room
    if room.hospital_id != session['user_id']:
        abort(403)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('admin_edit_room', room_id=room.id))

# Doctor Routes (unchanged)
@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        doctor = Doctor.query.filter_by(username=username).first()
        if doctor and check_password_hash(doctor.password, password):
            session['user_id'] = doctor.id
            session['role'] = 'doctor'
            return redirect(url_for('doctor_dashboard'))
        flash('Invalid username or password')
    return render_template('doctor_login.html')

@app.route('/doctor/dashboard', methods=['GET', 'POST'])
def doctor_dashboard():
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))
    doctor = db.session.get(Doctor, session['user_id'])
    if request.method == 'POST' and 'edit' in request.form:
        doctor.name = request.form['name']
        doctor.mobile = request.form['mobile']
        doctor.email = request.form['email']
        doctor.info = request.form['info']
        doctor.qualifications = request.form['qualifications']
        doctor.specializations = request.form['specializations']
        doctor.practice_years = int(request.form['practice_years'])
        doctor.additional_links = request.form['additional_links']
        doctor.practice_location = request.form['practice_location']
        db.session.commit()
        flash('Details updated')
    return render_template('doctor_dashboard.html', doctor=doctor)

@app.route('/doctor/manage_appointments', methods=['GET', 'POST'])
def doctor_manage_appointments():
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))
    doctor_id = session['user_id']
    time_slots = TimeSlot.query.filter_by(doctor_id=doctor_id).all()
    if request.method == 'POST':
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        price = float(request.form['price'])
        new_slot = TimeSlot(doctor_id=doctor_id, start_time=start_time, end_time=end_time, price=price)
        db.session.add(new_slot)
        db.session.commit()
        flash('Time slot added')
        return redirect(url_for('doctor_manage_appointments'))
    return render_template('manage_appointments.html', time_slots=time_slots)

@app.route('/doctor/delete_slot/<int:slot_id>')
def doctor_delete_slot(slot_id):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))
    slot = TimeSlot.query.get_or_404(slot_id)
    if slot.doctor_id != session['user_id']:
        abort(403)
    db.session.delete(slot)
    db.session.commit()
    flash('Time slot deleted')
    return redirect(url_for('doctor_manage_appointments'))

@app.route('/doctor/appointments')
def doctor_appointments():
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))
    doctor_id = session['user_id']
    today = date.today()
    # Join with TimeSlot to access time_slot information
    appointments = db.session.query(Appointment).join(TimeSlot).filter(
        Appointment.doctor_id == doctor_id, 
        Appointment.appointment_date == today, 
        Appointment.status == 'paid'
    ).all()
    return render_template('doctor_appointments.html', appointments=appointments, today_date=today)

@app.route('/doctor/medical_records', methods=['GET', 'POST'])
def doctor_medical_records():
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))
    doctor_id = session['user_id']
    search = request.args.get('search', '')
    if search:
        records = MedicalRecord.query.filter_by(doctor_id=doctor_id).filter(MedicalRecord.patient_name.like(f'%{search}%')).all()
    else:
        records = MedicalRecord.query.filter_by(doctor_id=doctor_id).all()
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        age = int(request.form['age'])
        mobile = request.form['mobile']
        medical_condition = request.form.get('medical_condition')
        file = request.files['file']
        if file and file.filename.endswith('.pdf'):
            folder = os.path.join(app.config['UPLOAD_FOLDER'], f'doctor_{doctor_id}')
            os.makedirs(folder, exist_ok=True)
            filename = secure_filename(file.filename)
            file_path = os.path.join(folder, filename)
            file.save(file_path)
            new_record = MedicalRecord(doctor_id=doctor_id, patient_name=patient_name, age=age, mobile=mobile, medical_condition=medical_condition, file_path=file_path)
            db.session.add(new_record)
            db.session.commit()
            flash('Medical record added')
        else:
            flash('Invalid file')
        return redirect(url_for('doctor_medical_records'))
    return render_template('medical_records.html', records=records, search=search)

@app.route('/doctor/delete_record/<int:record_id>')
def doctor_delete_record(record_id):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))
    record = MedicalRecord.query.get_or_404(record_id)
    if record.doctor_id != session['user_id']:
        abort(403)
    if os.path.exists(record.file_path):
        os.remove(record.file_path)
    db.session.delete(record)
    db.session.commit()
    flash('Medical record deleted')
    return redirect(url_for('doctor_medical_records'))

@app.route('/doctor/download_record/<int:record_id>')
def doctor_download_record(record_id):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))
    record = MedicalRecord.query.get_or_404(record_id)
    if record.doctor_id != session['user_id']:
        abort(403)
    return send_file(record.file_path, as_attachment=False)

@app.route('/doctor/manage_reviews')
def doctor_manage_reviews():
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))
    doctor_id = session['user_id']
    reviews = DoctorReview.query.filter_by(doctor_id=doctor_id).order_by(DoctorReview.created_at.desc()).all()
    return render_template('doctor_manage_reviews.html', reviews=reviews)

@app.route('/doctor/delete_review/<int:review_id>')
def doctor_delete_review(review_id):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))
    review = DoctorReview.query.get_or_404(review_id)
    if review.doctor_id != session['user_id']:
        abort(403)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('doctor_manage_reviews'))

# Ambulance Routes (updated and new)
@app.route('/ambulance/login', methods=['GET', 'POST'])
def ambulance_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        ambulance = Ambulance.query.filter_by(username=username).first()
        if ambulance and check_password_hash(ambulance.password, password):
            session['user_id'] = ambulance.id
            session['role'] = 'ambulance'
            return redirect(url_for('ambulance_dashboard'))
        flash('Invalid username or password')
    return render_template('ambulance_login.html')

@app.route('/ambulance/dashboard', methods=['GET', 'POST'])
def ambulance_dashboard():
    if 'role' not in session or session['role'] != 'ambulance':
        return redirect(url_for('ambulance_login'))
    ambulance = Ambulance.query.get(session['user_id'])
    if request.method == 'POST' and 'edit' in request.form:
        ambulance.name = request.form['name']
        ambulance.mobile = request.form['mobile']
        ambulance.email = request.form['email']
        ambulance.info = request.form['info']
        ambulance.status = request.form['status']
        db.session.commit()
        flash('Details updated')
    return render_template('ambulance_dashboard.html', ambulance=ambulance)

@app.route('/ambulance/vehicles', methods=['GET', 'POST'])
def ambulance_vehicles():
    if 'role' not in session or session['role'] != 'ambulance':
        return redirect(url_for('ambulance_login'))
    ambulance_id = session['user_id']
    vehicles = AmbulanceVehicle.query.filter_by(ambulance_id=ambulance_id).all()
    if request.method == 'POST' and 'add' in request.form:
        name = request.form['name']
        numberplate = request.form['numberplate']
        cost_price = float(request.form['cost_price'])
        medical_support = request.form.get('medical_support')
        file = request.files['image']
        image_path = None
        if file and file.filename != '':
            folder = os.path.join(app.config['UPLOAD_FOLDER'], f'ambulance_{ambulance_id}/vehicles')
            os.makedirs(folder, exist_ok=True)
            filename = secure_filename(file.filename)
            image_path = os.path.join(folder, filename)
            file.save(image_path)
        new_vehicle = AmbulanceVehicle(ambulance_id=ambulance_id, name=name, numberplate=numberplate, cost_price=cost_price, medical_support=medical_support, image_path=image_path)
        db.session.add(new_vehicle)
        db.session.commit()
        flash('Vehicle added')
        return redirect(url_for('ambulance_vehicles'))
    return render_template('ambulance_vehicles.html', vehicles=vehicles)

@app.route('/ambulance/edit_vehicle/<int:vehicle_id>', methods=['GET', 'POST'])
def ambulance_edit_vehicle(vehicle_id):
    if 'role' not in session or session['role'] != 'ambulance':
        return redirect(url_for('ambulance_login'))
    vehicle = AmbulanceVehicle.query.get_or_404(vehicle_id)
    if vehicle.ambulance_id != session['user_id']:
        abort(403)
    if request.method == 'POST':
        vehicle.name = request.form['name']
        vehicle.numberplate = request.form['numberplate']
        vehicle.cost_price = float(request.form['cost_price'])
        vehicle.medical_support = request.form.get('medical_support')
        file = request.files['image']
        if file and file.filename != '':
            if vehicle.image_path and os.path.exists(vehicle.image_path):
                os.remove(vehicle.image_path)
            folder = os.path.join(app.config['UPLOAD_FOLDER'], f'ambulance_{session["user_id"]}/vehicles')
            os.makedirs(folder, exist_ok=True)
            filename = secure_filename(file.filename)
            vehicle.image_path = os.path.join(folder, filename)
            file.save(vehicle.image_path)
        db.session.commit()
        flash('Vehicle updated')
        return redirect(url_for('ambulance_vehicles'))
    return render_template('ambulance_edit_vehicle.html', vehicle=vehicle)

@app.route('/ambulance/delete_vehicle/<int:vehicle_id>')
def ambulance_delete_vehicle(vehicle_id):
    if 'role' not in session or session['role'] != 'ambulance':
        return redirect(url_for('ambulance_login'))
    vehicle = AmbulanceVehicle.query.get_or_404(vehicle_id)
    if vehicle.ambulance_id != session['user_id']:
        abort(403)
    if vehicle.image_path and os.path.exists(vehicle.image_path):
        os.remove(vehicle.image_path)
    db.session.delete(vehicle)
    db.session.commit()
    flash('Vehicle deleted')
    return redirect(url_for('ambulance_vehicles'))

@app.route('/ambulance/bookings')
def ambulance_bookings():
    if 'role' not in session or session['role'] != 'ambulance':
        return redirect(url_for('ambulance_login'))
    ambulance_id = session['user_id']
    bookings = AmbulanceBooking.query.filter_by(ambulance_id=ambulance_id).all()
    pending_bookings = [b for b in bookings if b.status == 'pending']
    accepted_bookings = [b for b in bookings if b.status == 'accepted']
    paid_bookings = [b for b in bookings if b.status == 'paid']
    return render_template('ambulance_bookings.html', pending_bookings=pending_bookings, accepted_bookings=accepted_bookings, paid_bookings=paid_bookings)

@app.route('/ambulance/accept_booking/<int:booking_id>', methods=['GET', 'POST'])
def ambulance_accept_booking(booking_id):
    if 'role' not in session or session['role'] != 'ambulance':
        return redirect(url_for('ambulance_login'))
    booking = AmbulanceBooking.query.get_or_404(booking_id)
    if booking.ambulance_id != session['user_id']:
        abort(403)
    if request.method == 'POST':
        live_location_link = request.form['live_location_link']
        booking.live_location_link = live_location_link
        booking.status = 'accepted'
        vehicle = booking.vehicle
        patient = booking.patient
        pdf_buffer = generate_ambulance_bill_pdf(booking, vehicle)
        subject = "Ambulance Booking Accepted"
        body = f"Dear {patient.name},\n\nYour ambulance booking request has been accepted. Please pay the bill to confirm.\nLive Location Link: {live_location_link}\n\nBest regards,\nAmbulance Team"
        send_email(patient.email, subject, body, pdf_buffer)
        db.session.commit()
        flash('Booking accepted and email sent')
        return redirect(url_for('ambulance_bookings'))
    return render_template('ambulance_accept_booking.html', booking=booking)

@app.route('/ambulance/share_live_location/<int:booking_id>', methods=['GET', 'POST'])
def ambulance_share_live_location(booking_id):
    if 'role' not in session or session['role'] != 'ambulance':
        return redirect(url_for('ambulance_login'))
    booking = AmbulanceBooking.query.get_or_404(booking_id)
    if booking.ambulance_id != session['user_id'] or booking.status != 'accepted':
        abort(403)
    if request.method == 'POST':
        live_location_link = request.form['live_location_link']
        booking.live_location_link = live_location_link
        vehicle = booking.vehicle
        patient = booking.patient
        subject = "Ambulance Live Location Updated"
        body = f"Dear {patient.name},\n\nThe live location for your ambulance booking has been updated. Live Location Link: {live_location_link}\n\nBest regards,\nAmbulance Team"
        send_email(patient.email, subject, body)
        db.session.commit()
        flash('Live location shared and email sent')
        return redirect(url_for('ambulance_bookings'))
    return render_template('ambulance_share_live_location.html', booking=booking)

@app.route('/ambulance/reject_booking/<int:booking_id>')
def ambulance_reject_booking(booking_id):
    if 'role' not in session or session['role'] != 'ambulance':
        return redirect(url_for('ambulance_login'))
    booking = AmbulanceBooking.query.get_or_404(booking_id)
    if booking.ambulance_id != session['user_id']:
        abort(403)
    booking.status = 'rejected'
    patient = booking.patient
    subject = "Ambulance Booking Rejected"
    body = f"Dear {patient.name},\n\nYour ambulance booking request has been rejected.\n\nBest regards,\nAmbulance Team"
    send_email(patient.email, subject, body)
    db.session.commit()
    flash('Booking rejected')
    return redirect(url_for('ambulance_bookings'))

@app.route('/ambulance/reviews')
def ambulance_reviews():
    if 'role' not in session or session['role'] != 'ambulance':
        return redirect(url_for('ambulance_login'))
    ambulance_id = session['user_id']
    reviews = AmbulanceReview.query.filter_by(ambulance_id=ambulance_id).order_by(AmbulanceReview.created_at.desc()).all()
    return render_template('ambulance_reviews.html', reviews=reviews)

@app.route('/ambulance/delete_review/<int:review_id>')
def ambulance_delete_review(review_id):
    if 'role' not in session or session['role'] != 'ambulance':
        return redirect(url_for('ambulance_login'))
    review = AmbulanceReview.query.get_or_404(review_id)
    if review.ambulance_id != session['user_id']:
        abort(403)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('ambulance_reviews'))

# Nurse Routes (unchanged)
@app.route('/nurse/login', methods=['GET', 'POST'])
def nurse_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        nurse = Nurse.query.filter_by(username=username).first()
        if nurse and check_password_hash(nurse.password, password):
            session['user_id'] = nurse.id
            session['role'] = 'nurse'
            return redirect(url_for('nurse_dashboard'))
        flash('Invalid username or password')
    return render_template('nurse_login.html')

@app.route('/nurse/dashboard', methods=['GET', 'POST'])
def nurse_dashboard():
    if 'role' not in session or session['role'] != 'nurse':
        return redirect(url_for('nurse_login'))
    nurse = Nurse.query.get(session['user_id'])
    if request.method == 'POST' and 'edit' in request.form:
        nurse.name = request.form['name']
        nurse.mobile = request.form['mobile']
        nurse.email = request.form['email']
        nurse.info = request.form['info']
        db.session.commit()
        flash('Details updated')
    return render_template('nurse_dashboard.html', nurse=nurse)

# Canteen Routes (unchanged)
@app.route('/canteen/login', methods=['GET', 'POST'])
def canteen_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        canteen = Canteen.query.filter_by(username=username).first()
        if canteen and check_password_hash(canteen.password, password):
            session['user_id'] = canteen.id
            session['role'] = 'canteen'
            return redirect(url_for('canteen_dashboard'))
        flash('Invalid username or password')
    return render_template('canteen_login.html')

@app.route('/canteen/dashboard', methods=['GET', 'POST'])
def canteen_dashboard():
    if 'role' not in session or session['role'] != 'canteen':
        return redirect(url_for('canteen_login'))
    canteen = Canteen.query.get(session['user_id'])
    if request.method == 'POST' and 'edit' in request.form:
        canteen.name = request.form['name']
        canteen.mobile = request.form['mobile']
        canteen.email = request.form['email']
        canteen.info = request.form['info']
        db.session.commit()
        flash('Details updated')
    return render_template('canteen_dashboard.html', canteen=canteen)

# Patient Routes (updated and new)
@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        patient = Patient.query.filter_by(username=username).first()
        if patient and check_password_hash(patient.password, password):
            session['user_id'] = patient.id
            session['role'] = 'patient'
            return redirect(url_for('patient_dashboard'))
        flash('Invalid username or password')
    return render_template('patient_login.html')

@app.route('/patient/register', methods=['GET', 'POST'])
def patient_register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('patient_register.html')
        if Patient.query.filter_by(username=username).first() or Patient.query.filter_by(email=email).first():
            flash('Username or email already exists')
            return render_template('patient_register.html')
        hashed_password = generate_password_hash(password)
        new_patient = Patient(name=name, username=username, email=email, mobile=mobile, password=hashed_password)
        db.session.add(new_patient)
        db.session.commit()
        return redirect(url_for('patient_login'))
    return render_template('patient_register.html')

@app.route('/patient/dashboard', methods=['GET', 'POST'])
def patient_dashboard():
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    patient = Patient.query.get(session['user_id'])
    hospitals = Hospital.query.all()
    bookings = Booking.query.filter_by(patient_id=session['user_id']).all()
    pending_requests = [b for b in bookings if b.status == 'pending']
    accepted_unpaid = [b for b in bookings if b.status == 'accepted']
    history_bookings = [b for b in bookings if b.status in ['paid', 'rejected']]
    
    # Join appointments with time_slots to access time_slot information
    appointments = db.session.query(Appointment).join(TimeSlot).filter(
        Appointment.patient_id == session['user_id']
    ).all()
    history_appointments = [a for a in appointments if a.status == 'paid']
    
    # Ambulance
    ambulance_pending = AmbulanceBooking.query.filter_by(patient_id=session['user_id'], status='pending').all()
    ambulance_notifications = AmbulanceBooking.query.filter_by(patient_id=session['user_id'], status='accepted').all()
    ambulance_history = AmbulanceBooking.query.filter_by(patient_id=session['user_id'], status='paid').all()
    
    if request.method == 'POST' and 'edit' in request.form:
        patient.name = request.form['name']
        patient.mobile = request.form['mobile']
        patient.email = request.form['email']
        patient.info = request.form['info']
        db.session.commit()
        flash('Details updated')
    return render_template('patient_dashboard.html', patient=patient, hospitals=hospitals, pending_requests=pending_requests, accepted_unpaid=accepted_unpaid, history_bookings=history_bookings, history_appointments=history_appointments, ambulance_pending=ambulance_pending, ambulance_notifications=ambulance_notifications, ambulance_history=ambulance_history)

@app.route('/patient/hospital/<int:hospital_id>')
def patient_hospital(hospital_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    hospital = Hospital.query.get_or_404(hospital_id)
    doctors = Doctor.query.filter_by(hospital_id=hospital_id).all()
    ambulances = Ambulance.query.filter_by(hospital_id=hospital_id).all()
    nurses = Nurse.query.filter_by(hospital_id=hospital_id).all()
    canteens = Canteen.query.filter_by(hospital_id=hospital_id).all()
    rooms = Room.query.filter_by(hospital_id=hospital_id).all()
    return render_template('patient_hospital.html', hospital=hospital, doctors=doctors, ambulances=ambulances, nurses=nurses, canteens=canteens, rooms=rooms)

@app.route('/patient/ambulance/<int:ambulance_id>', methods=['GET', 'POST'])
def patient_ambulance(ambulance_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    ambulance = Ambulance.query.get_or_404(ambulance_id)
    vehicles = AmbulanceVehicle.query.filter_by(ambulance_id=ambulance_id).all()
    reviews = AmbulanceReview.query.filter_by(ambulance_id=ambulance_id).order_by(AmbulanceReview.created_at.desc()).all()
    return render_template('patient_ambulance.html', ambulance=ambulance, vehicles=vehicles, reviews=reviews)

@app.route('/patient/book_ambulance_normal/<int:vehicle_id>')
def patient_book_ambulance_normal(vehicle_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    vehicle = AmbulanceVehicle.query.get_or_404(vehicle_id)
    new_booking = AmbulanceBooking(
        ambulance_id=vehicle.ambulance_id,
        vehicle_id=vehicle_id,
        patient_id=session['user_id'],
        use_type='normal',
        amount=vehicle.cost_price,
        status='pending'
    )
    db.session.add(new_booking)
    db.session.commit()
    flash('Ambulance booking request sent')
    return redirect(url_for('patient_dashboard'))

@app.route('/patient/emergency_ambulance/<int:vehicle_id>', methods=['GET', 'POST'])
def patient_emergency_ambulance(vehicle_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    vehicle = AmbulanceVehicle.query.get_or_404(vehicle_id)
    if request.method == 'POST':
        location_link = request.form['location_link']
        new_booking = AmbulanceBooking(
            ambulance_id=vehicle.ambulance_id,
            vehicle_id=vehicle_id,
            patient_id=session['user_id'],
            use_type='emergency',
            location_link=location_link,
            amount=vehicle.cost_price * 2,
            status='accepted'
        )
        db.session.add(new_booking)
        db.session.commit()
        return redirect(url_for('patient_ambulance_bill', booking_id=new_booking.id))
    return render_template('emergency_book.html', vehicle=vehicle)

@app.route('/patient/ambulance_bill/<int:booking_id>')
def patient_ambulance_bill(booking_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    booking = AmbulanceBooking.query.get_or_404(booking_id)
    if booking.patient_id != session['user_id'] or booking.status != 'accepted':
        abort(403)
    vehicle = booking.vehicle
    return render_template('ambulance_bill.html', booking=booking, amount=booking.amount, vehicle=vehicle)

@app.route('/patient/ambulance_pay/<int:booking_id>')
def patient_ambulance_pay(booking_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    booking = AmbulanceBooking.query.get_or_404(booking_id)
    if booking.patient_id != session['user_id'] or booking.status != 'accepted':
        abort(403)
    amount = booking.amount
    order = razorpay_client.order.create({
        "amount": int(amount * 100),
        "currency": "INR",
        "receipt": f"ambulance_{booking_id}"
    })
    return render_template('payment.html', order=order, key=app.config['RAZORPAY_KEY_ID'], amount=amount, booking_id=booking_id, success_url=url_for('ambulance_payment_success', booking_id=booking_id))

@app.route('/ambulance_payment_success/<int:booking_id>', methods=['POST'])
def ambulance_payment_success(booking_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    params = {
        'razorpay_order_id': request.form['razorpay_order_id'],
        'razorpay_payment_id': request.form['razorpay_payment_id'],
        'razorpay_signature': request.form['razorpay_signature']
    }
    try:
        razorpay_client.utility.verify_payment_signature(params)
        booking = AmbulanceBooking.query.get_or_404(booking_id)
        if booking.patient_id != session['user_id']:
            abort(403)
        booking.status = 'paid'
        db.session.commit()
        flash('Payment successful! Ambulance booked.')
        patient = Patient.query.get(booking.patient_id)
        vehicle = booking.vehicle
        pdf_buffer = generate_ambulance_bill_pdf(booking, vehicle)
        subject = "Ambulance Booking Confirmed - Thank You!"
        body = f"Dear {patient.name},\n\nThank you for booking the ambulance. Please find the bill attached.\n\nBest regards,\nHospital Team"
        send_email(patient.email, subject, body, pdf_buffer)
        if booking.use_type == 'emergency':
            ambulance = Ambulance.query.get(booking.ambulance_id)
            emergency_subject = "Emergency Ambulance Request"
            emergency_body = f"Emergency request from {patient.name}. Go to this location link: {booking.location_link}. Please accept and share your live location."
            send_email(ambulance.email, emergency_subject, emergency_body)
    except Exception as e:
        print(f"Payment verification failed: {e}")
        flash('Payment verification failed.')
    return redirect(url_for('patient_dashboard'))

@app.route('/patient/add_ambulance_review/<int:ambulance_id>', methods=['POST'])
def patient_add_ambulance_review(ambulance_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    ambulance = Ambulance.query.get_or_404(ambulance_id)
    rating = int(request.form['rating'])
    text = request.form.get('text')
    new_review = AmbulanceReview(ambulance_id=ambulance_id, patient_id=session['user_id'], rating=rating, text=text)
    db.session.add(new_review)
    db.session.commit()
    flash('Review added')
    return redirect(url_for('patient_ambulance', ambulance_id=ambulance_id))

@app.route('/patient/edit_ambulance_review/<int:review_id>', methods=['GET', 'POST'])
def patient_edit_ambulance_review(review_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    review = AmbulanceReview.query.get_or_404(review_id)
    if review.patient_id != session['user_id']:
        abort(403)
    if request.method == 'POST':
        review.rating = int(request.form['rating'])
        review.text = request.form.get('text')
        db.session.commit()
        flash('Review updated')
        return redirect(url_for('patient_ambulance', ambulance_id=review.ambulance_id))
    return render_template('patient_edit_ambulance_review.html', review=review)

@app.route('/patient/delete_ambulance_review/<int:review_id>')
def patient_delete_ambulance_review(review_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    review = AmbulanceReview.query.get_or_404(review_id)
    if review.patient_id != session['user_id']:
        abort(403)
    ambulance_id = review.ambulance_id
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('patient_ambulance', ambulance_id=ambulance_id))

@app.route('/patient/doctor/<int:doctor_id>')
def patient_doctor(doctor_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    reviews = DoctorReview.query.filter_by(doctor_id=doctor_id).order_by(DoctorReview.created_at.desc()).all()
    return render_template('patient_doctor.html', doctor=doctor, reviews=reviews)

@app.route('/patient/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
def patient_book_appointment(doctor_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    time_slots = TimeSlot.query.filter_by(doctor_id=doctor_id).all()
    if request.method == 'POST':
        appointment_date = datetime.strptime(request.form['appointment_date'], '%Y-%m-%d').date()
        time_slot_id = int(request.form['time_slot_id'])
        # Check if slot is available
        existing = Appointment.query.filter_by(doctor_id=doctor_id, appointment_date=appointment_date, time_slot_id=time_slot_id, status='paid').first()
        if existing:
            flash('Slot not available')
            return redirect(url_for('patient_book_appointment', doctor_id=doctor_id))
        new_appointment = Appointment(doctor_id=doctor_id, patient_id=session['user_id'], appointment_date=appointment_date, time_slot_id=time_slot_id, status='accepted')  # Directly accepted for simplicity
        db.session.add(new_appointment)
        db.session.commit()
        return redirect(url_for('patient_appointment_bill', appointment_id=new_appointment.id))
    return render_template('book_appointment.html', doctor=doctor, time_slots=time_slots)

@app.route('/patient/appointment_bill/<int:appointment_id>')
def patient_appointment_bill(appointment_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.patient_id != session['user_id'] or appointment.status != 'accepted':
        abort(403)
    time_slot = TimeSlot.query.get(appointment.time_slot_id)
    amount = time_slot.price
    return render_template('appointment_bill.html', appointment=appointment, amount=amount, time_slot=time_slot, doctor=appointment.doctor)

@app.route('/patient/appointment_pay/<int:appointment_id>')
def patient_appointment_pay(appointment_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.patient_id != session['user_id'] or appointment.status != 'accepted':
        abort(403)
    time_slot = TimeSlot.query.get(appointment.time_slot_id)
    amount = time_slot.price
    order = razorpay_client.order.create({
        "amount": int(amount * 100),
        "currency": "INR",
        "receipt": f"appointment_{appointment_id}"
    })
    return render_template('appointment_payment.html', order=order, key=app.config['RAZORPAY_KEY_ID'], amount=amount, appointment_id=appointment_id, success_url=url_for('payment_success_appointment', appointment_id=appointment_id))

@app.route('/payment_success_appointment/<int:appointment_id>', methods=['POST'])
def payment_success_appointment(appointment_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    params = {
        'razorpay_order_id': request.form['razorpay_order_id'],
        'razorpay_payment_id': request.form['razorpay_payment_id'],
        'razorpay_signature': request.form['razorpay_signature']
    }
    try:
        razorpay_client.utility.verify_payment_signature(params)
        appointment = Appointment.query.get_or_404(appointment_id)
        if appointment.patient_id != session['user_id']:
            abort(403)
        appointment.status = 'paid'
        db.session.commit()
        flash('Payment successful! Appointment booked.')
        # Send email to patient with bill
        patient = Patient.query.get(appointment.patient_id)
        if patient and patient.email:
            time_slot = TimeSlot.query.get(appointment.time_slot_id)
            pdf_buffer = generate_appointment_bill_pdf(appointment, time_slot)
            subject = "Appointment Booked - Thank You!"
            body = f"Dear {patient.name},\n\nThank you for booking the appointment. Please find the bill attached.\n\nBest regards,\nHospital Team"
            send_email(patient.email, subject, body, pdf_buffer)
    except Exception as e:
        print(f"Payment verification failed: {e}")
        flash('Payment verification failed.')
    return redirect(url_for('patient_dashboard'))

@app.route('/patient/add_doctor_review/<int:doctor_id>', methods=['POST'])
def patient_add_doctor_review(doctor_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    rating = int(request.form['rating'])
    text = request.form['text']
    new_review = DoctorReview(doctor_id=doctor_id, patient_id=session['user_id'], rating=rating, text=text)
    db.session.add(new_review)
    db.session.commit()
    flash('Review added')
    return redirect(url_for('patient_doctor', doctor_id=doctor_id))

@app.route('/patient/edit_doctor_review/<int:review_id>', methods=['POST'])
def patient_edit_doctor_review(review_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    review = DoctorReview.query.get_or_404(review_id)
    if review.patient_id != session['user_id']:
        abort(403)
    review.rating = int(request.form['rating'])
    review.text = request.form['text']
    db.session.commit()
    flash('Review updated')
    return redirect(url_for('patient_doctor', doctor_id=review.doctor_id))

@app.route('/patient/delete_doctor_review/<int:review_id>')
def patient_delete_doctor_review(review_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    review = DoctorReview.query.get_or_404(review_id)
    if review.patient_id != session['user_id']:
        abort(403)
    doctor_id = review.doctor_id
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('patient_doctor', doctor_id=doctor_id))

@app.route('/patient/hospital/<int:hospital_id>/room/<int:room_id>')
def patient_room(hospital_id, room_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    room = Room.query.get_or_404(room_id)
    if room.hospital_id != hospital_id:
        abort(404)
    beds = Bed.query.filter_by(room_id=room_id).all()
    reviews = Review.query.filter_by(room_id=room_id).order_by(Review.created_at.desc()).all()
    return render_template('patient_room.html', room=room, beds=beds, hospital_id=hospital_id, reviews=reviews)

@app.route('/patient/book_bed', methods=['POST'])
def patient_book_bed():
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    bed_id = int(request.form['bed_id'])
    bed = Bed.query.get_or_404(bed_id)
    if bed.status != 'available':
        flash('Bed not available')
        return redirect(url_for('patient_room', hospital_id=bed.room.hospital_id, room_id=bed.room_id))
    room = Room.query.get(bed.room_id)
    hospital_id = room.hospital_id
    check_in_date = datetime.strptime(request.form['check_in_date'], '%Y-%m-%d').date()
    new_booking = Booking(
        bed_id=bed_id,
        patient_id=session['user_id'],
        patient_name=request.form['patient_name'],
        contact_number=request.form['contact_number'],
        age=int(request.form['age']),
        medical_condition=request.form.get('medical_condition'),
        estimated_stay=int(request.form['estimated_stay']),
        check_in_date=check_in_date
    )
    db.session.add(new_booking)
    db.session.commit()
    flash('Booking request sent')
    return redirect(url_for('patient_hospital', hospital_id=hospital_id))

@app.route('/patient/add_review/<int:room_id>', methods=['POST'])
def patient_add_review(room_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    room = Room.query.get_or_404(room_id)
    rating = int(request.form['rating'])
    text = request.form['text']
    new_review = Review(room_id=room_id, patient_id=session['user_id'], rating=rating, text=text)
    db.session.add(new_review)
    db.session.commit()
    flash('Review added')
    return redirect(url_for('patient_room', hospital_id=room.hospital_id, room_id=room_id))

@app.route('/patient/edit_review/<int:review_id>', methods=['POST'])
def patient_edit_review(review_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    review = Review.query.get_or_404(review_id)
    if review.patient_id != session['user_id']:
        abort(403)
    review.rating = int(request.form['rating'])
    review.text = request.form['text']
    db.session.commit()
    flash('Review updated')
    return redirect(url_for('patient_room', hospital_id=review.room.hospital_id, room_id=review.room_id))

@app.route('/patient/delete_review/<int:review_id>')
def patient_delete_review(review_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    review = Review.query.get_or_404(review_id)
    if review.patient_id != session['user_id']:
        abort(403)
    room_id = review.room_id
    hospital_id = review.room.hospital_id
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted')
    return redirect(url_for('patient_room', hospital_id=hospital_id, room_id=room_id))

@app.route('/patient/bill/<int:booking_id>')
def patient_bill(booking_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    booking = Booking.query.get_or_404(booking_id)
    if booking.patient_id != session['user_id'] or booking.status != 'accepted':
        abort(403)
    bed = Bed.query.get(booking.bed_id)
    room = Room.query.get(bed.room_id)
    amount = room.price_per_bed * booking.estimated_stay
    return render_template('bill.html', booking=booking, amount=amount, room=room, bed=bed)

@app.route('/patient/pay/<int:booking_id>')
def patient_pay(booking_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    booking = Booking.query.get_or_404(booking_id)
    if booking.patient_id != session['user_id'] or booking.status != 'accepted':
        abort(403)
    bed = Bed.query.get(booking.bed_id)
    room = Room.query.get(bed.room_id)
    amount = room.price_per_bed * booking.estimated_stay
    order = razorpay_client.order.create({
        "amount": int(amount * 100),
        "currency": "INR",
        "receipt": f"booking_{booking_id}"
    })
    return render_template('payment.html', order=order, key=app.config['RAZORPAY_KEY_ID'], amount=amount, booking_id=booking_id, success_url=url_for('payment_success', booking_id=booking_id))

@app.route('/payment_success/<int:booking_id>', methods=['POST'])
def payment_success(booking_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('patient_login'))
    params = {
        'razorpay_order_id': request.form['razorpay_order_id'],
        'razorpay_payment_id': request.form['razorpay_payment_id'],
        'razorpay_signature': request.form['razorpay_signature']
    }
    try:
        razorpay_client.utility.verify_payment_signature(params)
        booking = Booking.query.get_or_404(booking_id)
        if booking.patient_id != session['user_id']:
            abort(403)
        booking.status = 'paid'
        bed = Bed.query.get(booking.bed_id)
        bed.status = 'booked'
        db.session.commit()
        flash('Payment successful! Bed booked.')
        # Send email to patient with bill
        patient = Patient.query.get(booking.patient_id)
        if patient and patient.email:
            bed_obj = Bed.query.get(booking.bed_id)
            room = Room.query.get(bed_obj.room_id)
            pdf_buffer = generate_booking_bill_pdf(booking, bed_obj, room)
            subject = "Bed Booking Confirmed - Here are the Details and Bill"
            body = f"Dear {patient.name},\n\nYour bed booking is confirmed. Please find all details and the bill attached.\n\nBest regards,\nHospital Team"
            send_email(patient.email, subject, body, pdf_buffer)
    except Exception as e:
        print(f"Payment verification failed: {e}")
        flash('Payment verification failed.')
    return redirect(url_for('patient_dashboard'))

@app.route('/download_bill/<int:booking_id>')
def download_bill(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.status != 'paid':
        abort(403)
    if 'role' in session:
        if session['role'] == 'patient' and booking.patient_id != session['user_id']:
            abort(403)
        elif session['role'] == 'admin':
            bed = Bed.query.get(booking.bed_id)
            room = Room.query.get(bed.room_id)
            if room.hospital_id != session['user_id']:
                abort(403)
    else:
        abort(403)
    bed = Bed.query.get(booking.bed_id)
    room = Room.query.get(bed.room_id)
    buffer = generate_booking_bill_pdf(booking, bed, room)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"bill_{booking_id}.pdf", mimetype='application/pdf')

@app.route('/download_appointment_bill/<int:appointment_id>')
def download_appointment_bill(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.status != 'paid':
        abort(403)
    if 'role' in session:
        if session['role'] == 'patient' and appointment.patient_id != session['user_id']:
            abort(403)
        elif session['role'] == 'doctor' and appointment.doctor_id != session['user_id']:
            abort(403)
    else:
        abort(403)
    time_slot = TimeSlot.query.get(appointment.time_slot_id)
    buffer = generate_appointment_bill_pdf(appointment, time_slot)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"appointment_bill_{appointment_id}.pdf", mimetype='application/pdf')

@app.route('/patient/download_ambulance_bill/<int:booking_id>')
def patient_download_ambulance_bill(booking_id):
    booking = AmbulanceBooking.query.get_or_404(booking_id)
    if booking.status != 'paid':
        abort(403)
    if 'role' in session and session['role'] == 'patient' and booking.patient_id != session['user_id']:
        abort(403)
    vehicle = booking.vehicle
    buffer = generate_ambulance_bill_pdf(booking, vehicle)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"ambulance_bill_{booking_id}.pdf", mimetype='application/pdf')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)