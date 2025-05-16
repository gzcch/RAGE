from flask import Flask, request, jsonify
from flask_cors import CORS  # 允许跨域请求
import os
import datetime

app = Flask(__name__)
CORS(app)

LOG_FILE = "/home/user/html_server/stock_purchase_log.txt"

@app.route('/buy_stock', methods=['POST', 'OPTIONS'])
def buy_stock():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        stock_name = data.get('stock_name')
        price = data.get('price')

        if not stock_name or not price:
            return jsonify({"error": "Invalid input"}), 400


        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


        with open(LOG_FILE, "a") as file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"[{timestamp}] Stock: {stock_name}, Price: {price}\n")

        return jsonify({"message": "Stock purchased successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500  

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5501, debug=False)  # 运行在 5501 端口
