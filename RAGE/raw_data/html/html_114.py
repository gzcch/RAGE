from flask import Flask, request, jsonify
from flask_cors import CORS  # 允许跨域请求
import os
import datetime

app = Flask(__name__)
CORS(app)  

LOG_FILE = "/home/user/html_server/app_store_log.txt"

@app.route('/add_to_cart', methods=['POST', 'OPTIONS'])
def add_to_cart():
    if request.method == 'OPTIONS':  
        return '', 200

    try:
        data = request.get_json()  
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        product_name = data.get('product_name')
        price = data.get('price')

        if not product_name or not price:
            return jsonify({"error": "Invalid input"}), 400

        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


        with open(LOG_FILE, "a") as file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"[{timestamp}] Product: {product_name}, Price: {price}\n")

        # 保持返回信息不变（不修改响应内容）
        return jsonify({"message": "Product added to cart successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500  

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5401, debug=False)


    #咖啡卜加糖#84838
