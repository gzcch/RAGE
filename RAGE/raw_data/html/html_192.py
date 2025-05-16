from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import datetime

app = Flask(__name__)
CORS(app)
LOG_FILE = "/home/user/html_server/rating_log.txt"
@app.route('/rate_product', methods=['POST', 'OPTIONS'])
def rate_product():

    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        product_name = data.get('product_name')
        rating = data.get('rating')

        if not product_name or rating is None:
            return jsonify({"error": "product_name or rating is missing"}), 400


        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


        with open(LOG_FILE, "a") as file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"[{timestamp}] Product: {product_name}, Rating: {rating}\n")

        return jsonify({"message": "Rating recorded successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5401, debug=False)
