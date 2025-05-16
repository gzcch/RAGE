from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  

LOG_FILE = "confirmation_log.txt"

@app.route('/confirm', methods=['POST'])
def confirm_payment():
    try:
        data = request.get_json()  
        if not data or not data.get("confirmed"):
            return jsonify({"error": "Invalid request"}), 400

        with open(LOG_FILE, "a") as f:
            f.write("Payment confirmed\n")

        return jsonify({"message": "Payment confirmed successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500  

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5123, debug=False) 


