from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit
import random
import string
import os
from dotenv import load_dotenv
from twilio.rest import Client
from datetime import datetime
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
app = Flask(__name__)
socketio = SocketIO(app)

load_dotenv()

app.secret_key = 'MYSECRETKEY'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT') or 465)
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

mail = Mail(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    type_of_doctor = db.Column(db.String(120), nullable=True)
    user_type = db.Column(db.String(20), nullable=True)  # 'doctor', 'patient', or 'asha_worker'
    phone = db.Column(db.String(15), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    area_of_operation = db.Column(db.String(200), nullable=True)
    worker_id = db.Column(db.String(50), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    blood_group = db.Column(db.String(10), nullable=True)
    appointments = db.relationship("Appointment", foreign_keys="Appointment.user_id", back_populates="user")
    assigned_appointments = db.relationship("Appointment", foreign_keys="Appointment.asha_worker_id", back_populates="asha_worker")

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    asha_worker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)  # Patient name
    time_slot = db.Column(db.String(50), nullable=False)
    type_of_doctor = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    prescription_file = db.Column(db.String(255), nullable=True)
    user = db.relationship("User", foreign_keys=[user_id], back_populates="appointments")
    asha_worker = db.relationship("User", foreign_keys=[asha_worker_id], back_populates="assigned_appointments")

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', name='fk_doctor_user_id'), nullable=True)
    name = db.Column(db.String(80), nullable=False)
    specialty = db.Column(db.String(120), nullable=False)
    video_call_link = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(15), nullable=True)
    user = db.relationship('User', backref='doctor', uselist=False)

class Consultation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_name = db.Column(db.String(100), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    video_call_link = db.Column(db.String(255), nullable=True)
    doctor_joined = db.Column(db.Boolean, default=False)
    patient_joined = db.Column(db.Boolean, default=False)
    consultation_date = db.Column(db.DateTime, default=datetime.utcnow)

# Function to Generate Video Call Link
def generate_video_call_link(doctor_name):
    print(doctor_name, 'doctor_name')
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    room_name = f"{doctor_name.replace(' ', '')}_{timestamp}"
    return f"https://meet.jit.si/{room_name}"

notifications = []

def send_sms_notification(doctor_phone, patient_name, video_link):
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')
    doctor_phone = "+919946597321"
    # Debug: Print values to check if they're loaded
    print(f"TWILIO_ACCOUNT_SID: {account_sid}")
    print(f"TWILIO_AUTH_TOKEN: {auth_token}")
    print(f"TWILIO_PHONE_NUMBER: {twilio_phone}")
    print(f"Doctor Phone: {doctor_phone}")

    if not twilio_phone:
        print("Error: TWILIO_PHONE_NUMBER not set in environment variables")
        return None

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=f"Patient {patient_name} has joined the video call! Join here: {video_link}",
            from_=twilio_phone,
            to=doctor_phone
        )
        print("SMS Sent:", message.sid)
        return message.sid
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return None

def send_asha_sms_notification(asha_worker_phone, dr_name, patient_name):
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')
    asha_worker_phone = "+919946597321"
    # Debug: Print values to check if they're loaded
    print(f"TWILIO_ACCOUNT_SID: {account_sid}")
    print(f"TWILIO_AUTH_TOKEN: {auth_token}")
    print(f"TWILIO_PHONE_NUMBER: {twilio_phone}")

    if not twilio_phone:
        print("Error: TWILIO_PHONE_NUMBER not set in environment variables")
        return None

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=f"Prescription uploaded for ${patient_name} by ${dr_name}. Please check your account",
            from_=twilio_phone,
            to=asha_worker_phone
        )
        print("SMS Sent:", message.sid)
        return message.sid
    except Exception as e:
        print(f"Failed to send SMS: {e}")
        return None

# WebSocket Events
@socketio.on('connect', namespace='/doctor')
def doctor_connect():
    print('doctor connected')
    emit('message', {'data': 'Connected to doctor dashboard'})

@socketio.on('connect', namespace='/asha_worker')
def asha_connect():
    print('Asha worker connected')
    emit('message', {'data': 'Connected to Asha worker dashboard'})

@socketio.on('disconnect', namespace='/doctor')
def doctor_disconnect():
    print('Doctor disconnected')

@app.route('/send_notification', methods=['POST'])
def send_notification():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data received"}), 400

    notifications.append(data)
    print("New Notification:", data)

    return jsonify({"message": "Notification sent successfully!"}), 200


# API for Patient to Check if Doctor is Online
@app.route('/check-doctor-status/<int:consultation_id>', methods=['GET'])
def check_doctor_status(consultation_id):
    consultation = Consultation.query.get(consultation_id)
    if consultation:
        return jsonify({"doctor_joined": consultation.doctor_joined})
    return jsonify({"error": "Consultation not found"}), 404


def create_tables():
    with app.app_context():
        db.create_all()

def generate_random_string(length=10):
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))

    
# Set the path to the directory containing text files
text_files_dir = os.path.join(os.path.dirname(__file__), 'static/prescriptions')

# Set the path to the directory where PDFs will be saved
pdf_output_dir = os.path.join(os.path.dirname(__file__), 'static/pdfs')

# Function to convert text file to PDF
def convert_to_pdf(file_path, output_path):
    with open(file_path, 'r') as file:
        content = file.read()

    pdfkit.from_string(content, output_path, {'title': 'PDF Conversion', 'footer-center': '[page]/[topage]'})
    
# ============================================================ model ============================================================ 

def predict(symptoms):
    symptoms = [s.strip().lower() for s in symptoms]
    symptom_key = ",".join(sorted(symptoms))

    # Expanded list of possible diseases and their associated symptoms
    possible_diseases = {
        "fever,cough": ("Flu", 0.85, "General Physician"),
        "headache,nausea": ("Migraine", 0.75, "Neurologist"),
        "chest pain,shortness of breath": ("Heart Disease", 0.9, "Cardiologist"),
        "fever,headache": ("Dengue", 0.8, "General Physician"),
        "sore throat,fever": ("Strep Throat", 0.7, "ENT Specialist"),
        "fatigue,muscle pain": ("COVID-19", 0.88, "General Physician"),
        "abdominal pain,nausea": ("Gastritis", 0.7, "Gastroenterologist"),
        "joint pain,swelling": ("Arthritis", 0.75, "Rheumatologist"),
        "rash,itching": ("Allergy", 0.65, "Dermatologist"),
        "back pain": ("Muscle Strain", 0.6, "Orthopedist"),
    }

    # Try to find an exact match
    if symptom_key in possible_diseases:
        disease, confidence, specialty = possible_diseases[symptom_key]
    else:
        # Fallback: Find the best partial match
        best_match = None
        best_score = 0
        for key, value in possible_diseases.items():
            key_symptoms = key.split(',')
            match_score = len(set(symptoms).intersection(key_symptoms)) / len(key_symptoms)
            if match_score > best_score:
                best_match = value
                best_score = match_score

        if best_match:
            disease, confidence, specialty = best_match
        else:
            disease, confidence, specialty = ("Unknown Disease", 0.5, "General Physician")

    # Find a doctor with the matching specialty
    doctor = Doctor.query.filter_by(specialty=specialty).first()
    if doctor:
        video_conference_link = generate_video_call_link(doctor.name)
    else:
        video_conference_link = generate_video_call_link("General Physician")

    return disease, confidence, doctor, video_conference_link
# ============================================================ routes ============================================================ 

@app.route('/', methods=['GET', 'POST'])
def index():
    username = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        username = user.username
        if user.user_type == 'doctor':
            appointments = Appointment.query.filter_by(type_of_doctor=user.type_of_doctor).all()
            return render_template('doctor-dashboard.html', user=user, username=username, appointments=appointments)
        elif user.user_type == 'patient':
            user_appointments = user.appointments
            return render_template('patient-dashboard.html', username=username, user_appointments=user_appointments)
        else:
            return render_template('ashaworker-dashboard.html', username=username, user=user)
            
    return render_template('index.html')

@app.route('/profile/<user_type>', methods=['GET', 'POST'])
def profile(user_type):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.session.get(User, session['user_id'])
    
    if request.method == 'POST':
        # Update common fields
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        user.gender = request.form.get('gender')
        user.age = request.form.get('age')
        user.blood_group = request.form.get('blood_group')
        # Handle date of birth
        dob_str = request.form.get('date_of_birth')
        if dob_str:
            try:
                user.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format', 'error')
                return redirect(url_for('profile', user_type=user_type))
        
        # Update type-specific fields
        if user_type == 'asha_worker':
            user.area_of_operation = request.form.get('area_of_operation')
            user.worker_id = request.form.get('worker_id')
        
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except:
            db.session.rollback()
            flash('Error updating profile', 'error')
        
        return redirect(url_for('profile', user_type=user_type))
    
    template_map = {
        'doctor': 'doctor-profile.html',
        'patient': 'patient-profile.html',
        'asha_worker': 'asha-profile.html'
    }
    
    return render_template(template_map[user_type], 
                         user=user,
                         username=user.username,
                         Email=user.email,
                         user_appointments=user.appointments)

@app.route('/patient-register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_type = 'patient'
        try:
            user = User(username=username, email=email, password=password, user_type=user_type)
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            return redirect(url_for('register'))
        except IntegrityError:
            db.session.rollback()
            flash('Username already exists. Please choose a different username.', 'error')
    return render_template('patient-register.html')

@app.route('/doctor_register', methods=['GET', 'POST'])
def doctor_register():
    if request.method == 'POST':
        username1 = request.form['username']
        email1 = request.form['email']
        password1 = request.form['password']
        type_of_doctor1 = request.form['type_of_doctor']
        phonenumber = request.form['phonenumber']
        user_type = 'doctor'

        # Check if username already exists
        existing_user = db.session.get(User, username1)
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('doctor_login'))

        # Create new User
        new_user = User(
            username=username1,
            email=email1,
            phone=phonenumber,
            password=password1,
            type_of_doctor=type_of_doctor1,
            user_type=user_type,
        )
        db.session.add(new_user)

        # Flush to get the user ID before committing
        db.session.flush()

        # Create corresponding Doctor entry
        new_doctor = Doctor(
            user_id=new_user.id,  # Link to the new User
            name=username1,  # Use username as name (or add a 'name' field to the form)
            phone_number=phonenumber,
            specialty=type_of_doctor1,  # Use type_of_doctor as specialty
        )
        db.session.add(new_doctor)

        try:
            db.session.commit()
            flash('Doctor registered successfully! Please login.', 'success')
            return redirect(url_for('doctor_login'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during registration: {str(e)}', 'danger')
            return redirect(url_for('doctor_register'))

    return render_template('doctor-register.html')

@app.route('/asha-register', methods=['GET', 'POST'])
def asha_register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        worker_id = request.form['worker_id']
        area_of_operation = request.form['area_of_operation']
        user_type = 'asha_worker'
        try:
            user = User(username=username, email=email, password=password, worker_id=worker_id, area_of_operation=area_of_operation, user_type=user_type)
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            return redirect(url_for('asha_login'))
        except IntegrityError:
            db.session.rollback()
            flash('Username already exists. Please choose a different username.', 'error')
    return render_template('ashaworker-register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/patient-dashboard')
def patient_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('patient_login'))
    return render_template('patient-dashboard.html')

@app.route('/patient-login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        flash('Invalid credentials', 'error')
    return render_template('patient-login.html')


@app.route('/approve_appointment/<int:appointment_id>', methods=['GET'])
def approve_appointment(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.type_of_doctor:
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    # Check if this doctor is authorized to approve (based on specialty)
    if appointment.type_of_doctor != user.type_of_doctor:
        flash('You are not authorized to approve this appointment', 'error')
        return redirect(url_for('index'))
    
    # Update appointment status
    appointment.status = 'Approved'
    try:
        db.session.commit()
        flash('Appointment approved successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving appointment: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/doctor-login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        username1 = request.form['username']
        password1 = request.form['password']

        # Find user in database
        user = User.query.filter_by(username=username1).first()

        if user and user.password == password1:  # Use password hashing in real cases
            session['user_id'] = user.id
            session['username'] = user.username

            # Redirect doctor to doctor-dashboard
            if user.user_type == "doctor":
                return redirect(url_for('index'))

            return redirect(url_for('index'))

        flash('Invalid username or password', 'danger')

    return render_template('doctor-login.html')


@app.route('/asha-login', methods=['GET', 'POST'])
def asha_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password, user_type='asha_worker').first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        flash('Invalid credentials', 'error')
    return render_template('asha-login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/policy')
def policy():
    return render_template('privacy-policy.html')

@app.route('/admin')
def admin():
    username = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        username = user.username
        return render_template('admin.html',username=username)
    return render_template('index.html')


@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if 'user_id' not in session:
        flash('Please log in to access the chatbot.', 'error')
        return redirect(url_for('login'))
        
    user = db.session.get(User, session['user_id'])
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('login'))
    
    # Check if age or blood_group is missing
    if not user.age or not user.blood_group:
        flash('Please update your profile with age and blood group before using the chatbot.', 'warning')
        return redirect(url_for('profile', user_type='patient'))
    
    if request.method == 'POST':
        try:
            if not request.is_json:
                return jsonify({"error": "Request must be JSON"}), 400
            data = request.get_json()
            user_input = data.get('user_input')
            if not user_input:
                return jsonify({"error": "Missing 'user_input' field"}), 400
    
            symptoms = user_input.split(',')
            predicted_disease, confidence_score, doctor, video_conference_link = predict(symptoms)

            if doctor:
                doctor_name = doctor.name
                doctor_phone_number = doctor.phone_number
                specialty = doctor.specialty
            else:
                doctor_name = "General Physician"
                doctor_phone_number = "+919778229882"
                specialty = "General Medicine"

            if 'user_id' not in session:
                return jsonify({"error": "User not logged in"}), 401
            user = db.session.get(User, session['user_id'])
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            asha_worker = User.query.filter_by(user_type='asha_worker').first()
            if not asha_worker:
                return jsonify({"error": "No ASHA worker available"}), 503

            consultation = Consultation(
                doctor_name=doctor_name,
                patient_name=user.username,
                video_call_link=video_conference_link
            )
            db.session.add(consultation)
            db.session.flush()

            appointment = Appointment(
                user_id=user.id,
                name=user.username,
                time_slot="Immediate",  # Adjust as needed
                type_of_doctor=specialty,
                status='Pending',
                asha_worker_id=asha_worker.id  # Assign ASHA worker
            )
            db.session.add(appointment)
            db.session.commit()

            join_url = url_for('join_video', consultation_id=consultation.id, _external=True)
            # Notify ASHA worker via SocketIO
            socketio.emit('appointment_assigned', {
                'appointment_id': appointment.id,
                'patient_name': user.username,
                'doctor_name': doctor_name,
                'time_slot': appointment.time_slot
            }, namespace='/asha_worker')
            response = {
                "disease": predicted_disease,
                "confidence": confidence_score,
                "message": f"Based on your symptoms, you might have {predicted_disease}. Please consult {doctor_name}.",
                "video_link": join_url,
                "doctor_name": doctor_name,
                "consultation_id": consultation.id
            }
            return jsonify(response)
        except Exception as e:
            print(f"Error in /chatbot route: {e}")
            db.session.rollback()
            return jsonify({"error": "An error occurred"}), 500
    return render_template('chatbot.html')


@app.route('/join_video/<int:consultation_id>')
def join_video(consultation_id):
    consultation = Consultation.query.get_or_404(consultation_id)
    print(consultation,'consultations')
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if not user.type_of_doctor:  # Patient
            consultation.patient_joined = True  # Mark patient as joined
            db.session.commit()
            # Notify doctor via WebSocket and SMS
            socketio.emit('patient_joined', {
                'patient_name': user.username,
                'video_link': consultation.video_call_link,
                'consultation_id': consultation_id
            }, namespace='/doctor')
            doctor = Doctor.query.filter_by(name=consultation.doctor_name).first()
            print(doctor, 'doctor')
            if doctor:
                print(doctor.phone_number, 'phonenumber')
                send_sms_notification(doctor.phone_number, user.username, consultation.video_call_link)
        return redirect(consultation.video_call_link)  # Redirect to Jitsi URL
    
    # For doctors, redirect to dashboard (they join via /doctor_join_consultation)
    if user.type_of_doctor:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/doctor_join_consultation/<int:consultation_id>', methods=['GET'])
def doctor_join_consultation(consultation_id):
    print('join function called')
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.type_of_doctor:
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    consultation = Consultation.query.get_or_404(consultation_id)
    doctor = Doctor.query.filter_by(name=consultation.doctor_name).first()
    
    if not doctor or doctor.name != user.username:
        flash('You are not assigned to this consultation', 'error')
        return redirect(url_for('index'))
    
    # Update consultation status
    consultation.doctor_joined = True
    try:
        db.session.commit()
        flash('Consultation started successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error starting consultation: {str(e)}', 'error')
        return redirect(url_for('index'))
    
    # Notify ASHA workers
    socketio.emit('doctor_joined', {
        'doctor_name': user.username,
        'video_link': consultation.video_call_link,
        'consultation_id': consultation_id
    }, namespace='/asha_worker')
    
    return redirect(consultation.video_call_link)



import os
from werkzeug.utils import secure_filename

# Configure upload folder
UPLOAD_FOLDER = 'static/prescriptions'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/doctor_patients', methods=['GET'])
def doctor_patients():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.type_of_doctor:
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    # Fetch appointments for this doctor's specialty
    appointments = Appointment.query.filter_by(type_of_doctor=user.type_of_doctor).all()
    return render_template('doctor-patients.html', appointments=appointments, username=user.username)

@app.route('/upload_prescription/<int:appointment_id>', methods=['GET', 'POST'])
def upload_prescription(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.type_of_doctor:
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.type_of_doctor != user.type_of_doctor:
        flash('You are not authorized to upload a prescription for this appointment', 'error')
        return redirect(url_for('doctor_patients'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            appointment.prescription_file = file_path
            appointment.status = 'Prescribed'
            db.session.commit()
            flash('Prescription uploaded successfully', 'success')
            asha_worker = appointment.asha_worker
            asha_worker_phone = asha_worker.phone
            send_asha_sms_notification(asha_worker_phone, user.username, appointment.name)
            socketio.emit('prescription_uploaded', {
                'appointment_id': appointment_id,
                'doctor_name': user.username,
                'patient_name': appointment.name
            }, namespace='/asha_worker')
            return redirect(url_for('doctor_patients'))
        else:
            flash('Invalid file type. Allowed: pdf, doc, docx', 'error')
    
    return render_template('upload_prescription.html', appointment=appointment)

# Assuming this route exists for prescribing medicine
@app.route('/prescribe_medicine/<int:appointment_id>')
def prescribe_medicine(appointment_id):
    # Redirect to upload_prescription for consistency
    return redirect(url_for('upload_prescription', appointment_id=appointment_id))

@app.route('/view_prescription/<int:appointment_id>')
def view_prescription(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if not appointment.prescription_file:
        flash('No prescription available', 'error')
        return redirect(url_for('doctor_patients'))
    return send_file(appointment.prescription_file, as_attachment=False)
@app.route('/download_prescription/<int:appointment_id>')

def download_prescription(appointment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = db.session.get(User, session['user_id'])
    if not user or user.user_type != 'asha_worker':
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.asha_worker_id != user.id:
        flash('You are not assigned to this appointment', 'error')
        return redirect(url_for('index'))
    
    if not appointment.prescription_file:
        flash('No prescription available', 'error')
        return redirect(url_for('index'))
    
    return send_file(appointment.prescription_file, as_attachment=True, download_name=f"prescription_{appointment_id}.{appointment.prescription_file.split('.')[-1]}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create all database tables
    app.run(debug=True)