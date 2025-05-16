from flask import Flask, request, jsonify
from flask_cors import CORS  # 允许跨域请求
import datetime
import os

app = Flask(__name__)
CORS(app)  

LOG_FILE = "/home/user/html_server/log_rating.txt"

@app.route('/submit_rating', methods=['POST'])
def submit_rating():
    try:

        data = request.get_json()
        if not data:
            return jsonify({"message": "Invalid JSON format"}), 400

        restaurant = data.get("restaurant", "Unknown Restaurant")
        rating = int(data.get("rating"))


        # print(rating)
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({"message": "Rating must be an integer between 1 and 5"}), 400

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} - {restaurant}: {rating} stars\n"


        log_dir = os.path.dirname(LOG_FILE)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)


        with open(LOG_FILE, "a") as log_file:
            log_file.write(log_entry)

        print(f"✅ Rating recorded: {log_entry.strip()}")  # 终端调试日志

        return jsonify({"message": "Rating submitted successfully!"})
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"message": "An error occurred", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5222)
