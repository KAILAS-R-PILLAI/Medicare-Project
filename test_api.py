import requests

test_data = {
    "doctor_name": "Dr. Archana",
    "patient_name": "ammu",
    "room_id": "https://meet.jit.si/Dr.Archana_20250228150938"
}

response = requests.post("http://127.0.0.1:5000/send_notification", json=test_data)

print("Status Code:", response.status_code)
print("Raw Response:", response.text)