step 1: Go to folder where the app.py file is located
step 2: python -m venv medicare-env
step 3: medicare-env\Scripts\activate
step 3: pip install -r requirements.txt
step 4: python app.py

# only if required:
# initiate database setup.(I have already done this, in case if you need follow the steps below after deleting the database file from instance folder.)
flask db init
flask db migrate -m "Initial schema with all tables"
flask db upgrade

# Project structure
medicare-telemedicine/
├── app.py                # Main Flask application
├── medicare-env/         # Virtual environment
├── migrations/           # Database migrations (created by flask db init)
├── static/
│   ├── css/
│   │   └── style.css     # Main stylesheet
│   ├── images/
│   │   ├── heart-pulse-solid.svg
│   │   └── health-worker-animate.png
│   ├── js/
│   │   └── script.js     # Custom JavaScript
│   └── prescriptions/    # Uploaded prescription files
├── templates/
│   ├── index.html        # Homepage
│   ├── doctor-dashboard.html
│   ├── patient-dashboard.html
│   ├── ashaworker-dashboard.html
│   ├── chatbot.html
│   ├── upload_prescription.html
│   └── patient-profile.html
└── requirements.txt      # Dependencies