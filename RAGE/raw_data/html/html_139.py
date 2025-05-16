from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS to allow frontend to access API

LOG_FILE = "/home/user/html_server/flight_booking_log.txt"  # Change path as needed

@app.route('/book_flight', methods=['POST', 'OPTIONS'])
def book_flight():
    if request.method == 'OPTIONS':
        return '', 200  # Handle CORS preflight requests

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        flight_number = data.get('flight_number')
        price = data.get('price')
        departure = data.get('departure')
        departure_time = data.get('departure_time')

        if not flight_number or not price:
            return jsonify({"error": "Invalid input"}), 400

        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

        with open(LOG_FILE, "a") as file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"[{timestamp}] Flight: {flight_number}, Price: ${price}, {departure}, Departure: {departure_time}\n")

        return jsonify({"message": "Flight booked successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5401, debug=False)
