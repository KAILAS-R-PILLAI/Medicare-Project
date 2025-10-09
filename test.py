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
    role = db.Column(db.String(20), nullable=False, default='patient')
    type_of_doctor = db.Column(db.String(120), nullable=True)
    appointments = db.relationship("Appointment", back_populates="user")

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship("User", back_populates="appointments")
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'))
    doctor = db.relationship("Doctor")
    status = db.Column(db.String(20), default='Pending')

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    specialty = db.Column(db.String(120), nullable=False)
    video_call_link = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)

@app.route('/admin')
def admin_dashboard():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'admin':
            users = User.query.all()
            doctors = Doctor.query.all()
            appointments = Appointment.query.all()
            return render_template('admin-dashboard.html', users=users, doctors=doctors, appointments=appointments)
        else:
            flash('Access denied!', 'error')
            return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/admin/delete-user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'admin':
            user_to_delete = User.query.get(user_id)
            if user_to_delete:
                db.session.delete(user_to_delete)
                db.session.commit()
                flash('User deleted successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
    flash('Access denied!', 'error')
    return redirect(url_for('index'))

@app.route('/admin/delete-appointment/<int:appointment_id>')
def delete_appointment(appointment_id):
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'admin':
            appointment = Appointment.query.get(appointment_id)
            if appointment:
                db.session.delete(appointment)
                db.session.commit()
                flash('Appointment deleted successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
    flash('Access denied!', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
