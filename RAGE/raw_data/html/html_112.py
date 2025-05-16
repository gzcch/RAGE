from flask import Flask, request, jsonify
from flask_cors import CORS  # 允许跨域请求
import datetime
import os

app = Flask(__name__)
CORS(app)

LOG_FILE = "/home/user/html_server/log_clothing_rating.txt"

@app.route('/submit_rating', methods=['POST'])
def submit_rating():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Invalid JSON format"}), 400

        clothing = data.get("clothing", "Unknown Clothing")
        color = data.get("color", "Unknown Color")

        if not color:
            return jsonify({"message": "Color selection is required"}), 400

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} - {clothing}: {color}\n"

        log_dir = os.path.dirname(LOG_FILE)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        with open(LOG_FILE, "a") as log_file:
            log_file.write(log_entry)

        print(f"Rating recorded: {log_entry.strip()}")

        return jsonify({"message": "Color rating submitted successfully!"})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"message": "An error occurred", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5222)
