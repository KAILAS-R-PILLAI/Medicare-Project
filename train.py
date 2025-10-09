from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mail import Mail, Message
import random
import string
import os
from dotenv import load_dotenv
from twilio.rest import Client
from datetime import datetime

app = Flask(__name__)
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

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    type_of_doctor = db.Column(db.String(120), nullable=True)
    appointments = db.relationship("Appointment", back_populates="user")

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship("User", back_populates="appointments")

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    specialty = db.Column(db.String(120), nullable=False)
    video_call_link = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)



def generate_video_call_link(doctor_name):
    # Create a unique room name using the doctor's name and timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    room_name = f"{doctor_name.replace(' ', '')}_{timestamp}"
    return f"https://meet.jit.si/{room_name}"

def initialize_doctors():
    doctors = [
        Doctor(
            name="Dr. Anand",
            specialty="General Physician",
            video_call_link=generate_video_call_link("Dr. Anand"),  # Generate a unique link
            phone_number="+919778229882"
        ),
        Doctor(
            name="Dr. Archana",
            specialty="Neurologist",
            video_call_link=generate_video_call_link("Dr. Archana"),  # Generate a unique link
            phone_number="+17435002186"
        ),
        # Add more doctors as needed
    ]
    for doctor in doctors:
        db.session.add(doctor)
    db.session.commit()


def send_sms_alert(doctor_phone_number, message):
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=message,
        from_=os.getenv('TWILIO_PHONE_NUMBER'),
        to=doctor_phone_number
    )
    return message.sid



def create_tables():
    with app.app_context():
        db.create_all()

def generate_random_string(length=10):
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))

# def send_mail(subject, recipient, body):
#     msg = Message(subject, recipients=[recipient])
#     msg.body = body
#     mail.send(msg)
    
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
        if user.type_of_doctor:
            appointments = Appointment.query.filter_by(type_of_doctor=user.type_of_doctor).all()
            return render_template('doctor-dashboard.html', username=username, appointments=appointments)
            
        else:
            user_appointments = user.appointments
            return render_template('patient-dashboard.html', username=username, user_appointments=user_appointments)
            
    return render_template('index.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    username = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        username = user.username
        Email = user.email 
        user_appointments = user.appointments
        return render_template('patient-profile.html', username=username,Email=Email, user_appointments=user_appointments)
    return render_template('index')

@app.route('/patient-register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        try:
            user = User(username=username, email=email, password=password)
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            return redirect(url_for('index'))
        except IntegrityError:
            db.session.rollback()
            flash('Username already exists. Please choose a different username.', 'error')
    return render_template('patient-register.html')

@app.route('/doctor-register', methods=['GET', 'POST'])
def doctor_register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        type_of_doctor = request.form['type_of_doctor']
        user = User(username=username,email=email, password=password, type_of_doctor=type_of_doctor)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        return redirect(url_for('index'))
    return render_template('doctor-register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            flash('Wrong username or password. Please try again.', 'error')
    return render_template('login.html')

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

# @app.route('/videocall')
# def videocall():
#     if 'user_id' in session:
#         user = db.session.get(User, session['user_id'])
#         username = user.username
#         doctor_id = request.args.get('doctor_id')
#         doctor = db.session.get(Doctor, doctor_id)
        
#         if doctor:
#             video_conference_link = doctor.video_call_link
#             doctor_name = doctor.name
#             message = f"Patient {username} is trying to connect with you for a video consultation."
#             send_sms_alert(doctor.phone_number, message)
#         else:
#             video_conference_link = "https://meet.jit.si/DefaultRoom"  # Fallback link
#             doctor_name = "General Physician"
        
#         return render_template('videocall.html', username=username, video_link=video_conference_link, doctor_name=doctor_name)
#     return redirect(url_for('index'))

@app.route('/doctor-patients')
def doctor_patients():
    username = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        username = user.username
        doctor = User.query.get(session['user_id'])
        if not doctor.type_of_doctor:
            return redirect(url_for('index'))
        appointments = Appointment.query.filter_by(type_of_doctor=doctor.type_of_doctor).all()
        file_list = os.listdir(text_files_dir)
        return render_template('doctor-patients.html', doctor=doctor, appointments=appointments,username=username,file_list=file_list)
    return render_template('index.html')

# from twilio.rest import Client
import os

def send_sms_alert(doctor_phone_number, message):
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    try:
        message = client.messages.create(
            body=message,
            from_=os.getenv('TWILIO_PHONE_NUMBER'),
            to=doctor_phone_number
        )
        print(f"SMS sent successfully! SID: {message.sid}")
        return message.sid
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return None

@app.route('/send-sms-alert', methods=['POST'])
def send_sms_alert_route():
    try:
        data = request.get_json()
        doctor_phone_number = data.get('doctor_phone_number')
        patient_name = data.get('patient_name')

        if not doctor_phone_number or not patient_name:
            return jsonify({"error": "Missing required fields"}), 400

        # Send SMS alert
        message = f"Patient {patient_name} is trying to connect with you for a video consultation."
        sms_sid = send_sms_alert(doctor_phone_number, message)

        if sms_sid:
            return jsonify({"status": "SMS sent successfully", "sms_sid": sms_sid}), 200
        else:
            return jsonify({"error": "Failed to send SMS"}), 500

    except Exception as e:
        print(f"Error in /send-sms-alert route: {e}")
        return jsonify({"error": "An error occurred while sending the SMS."}), 500
# @app.route('/chatbot', methods=['GET', 'POST'])
# def chatbot():
#     if request.method == 'POST':
#         try:
#             user_input = request.form['user_input']
#             print("User input:", user_input)  # Log the user input
#             symptoms = user_input.split(',')
#             predicted_disease, confidence_score, doctor, video_conference_link = predict(symptoms)
            
#             if doctor:
#                 doctor_name = doctor.name
#             else:
#                 doctor_name = "General Physician"
            
#             response = {
#                 "disease": predicted_disease,
#                 "confidence": confidence_score,
#                 "message": f"Based on your symptoms, you might have {predicted_disease}. Please consult Dr. {doctor_name}.",
#                 "video_link": video_conference_link,
#                 "doctor_name": doctor_name
#             }
#             print("Response:", response)  # Log the response
#             return jsonify(response)
#         except Exception as e:
#             print(f"Error in /chatbot route: {e}")
#             return jsonify({"error": "An error occurred while processing your request."}), 500
#     return render_template('chatbot.html')

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        try:
            # Check if the request contains JSON data
            if not request.is_json:
                return jsonify({"error": "Request must be JSON"}), 400

            # Parse JSON data
            data = request.get_json()
            user_input = data.get('user_input')

            # Validate user input
            if not user_input:
                return jsonify({"error": "Missing 'user_input' field"}), 400

            # Process user input
            symptoms = user_input.split(',')
            print("User input:", user_input)  # Log the user input

            # Call the predict function
            predicted_disease, confidence_score, doctor, video_conference_link = predict(symptoms)

            # Handle doctor data
            if doctor:
                doctor_name = doctor.name
                doctor_phone_number = doctor.phone_number
            else:
                doctor_name = "General Physician"
                doctor_phone_number = "+919778229882"  # Default doctor's phone number

            # Prepare response
            response = {
                "disease": predicted_disease,
                "confidence": confidence_score,
                "message": f"Based on your symptoms, you might have {predicted_disease}. Please consult Dr. {doctor_name}.",
                "video_link": video_conference_link,
                "doctor_name": doctor_name,
                "doctor_phone_number": doctor_phone_number,
            }
            print("Response:", response)  # Log the response
            return jsonify(response)

        except Exception as e:
            print(f"Error in /chatbot route: {e}")
            return jsonify({"error": "An error occurred while processing your request."}), 500

    # Handle GET requests (render the chatbot form)
    return render_template('chatbot.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create all database tables
        initialize_doctors()  # Initialize doctors
    app.run(debug=True)