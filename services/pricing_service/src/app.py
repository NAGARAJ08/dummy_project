import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify
import uuid
import random
import time

app = Flask(__name__)

# Configure JSON logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
file_handler = logging.FileHandler('logs/pricing_service.log')
formatter = logging.Formatter('{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "pricing_service", "trace_id": "%(trace_id)s", "message": "%(message)s", "extra": %(extra)s}')
handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(file_handler)

# Mock price computation
def compute_price(symbol):
    # Simulate some computation time
    time.sleep(random.uniform(0.1, 0.5))
    base_prices = {"AAPL": 150.0, "GOOGL": 2800.0, "MSFT": 300.0}
    return base_prices.get(symbol, 100.0) + random.uniform(-5, 5)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "pricing_service"})

@app.route('/prices', methods=['POST'])
def compute_trade_price():
    trace_id = request.headers.get('X-Trace-Id', str(uuid.uuid4()))
    logging.info("Received price computation request", extra={"trace_id": trace_id, "endpoint": "/prices", "method": "POST"})
    
    data = request.get_json()
    if not data:
        logging.error("Invalid JSON payload", extra={"trace_id": trace_id})
        return jsonify({"error": "Invalid JSON"}), 400
    
    trade_id = data.get('trade_id')
    symbol = data.get('symbol')
    quantity = data.get('quantity')
    
    if not trade_id or not symbol or quantity is None:
        logging.error("Missing trade_id, symbol, or quantity", extra={"trace_id": trace_id})
        return jsonify({"error": "Missing trade_id, symbol, or quantity"}), 400
    
    # Simulate occasional timeout
    if random.random() < 0.1:  # 10% chance
        time.sleep(5)  # Timeout
        logging.error("Price computation timed out", extra={"trace_id": trace_id, "trade_id": trade_id})
        return jsonify({"error": "Timeout"}), 504
    
    computed_price = compute_price(symbol)
    
    logging.info("Price computed successfully", extra={"trace_id": trace_id, "trade_id": trade_id, "symbol": symbol, "computed_price": computed_price})
    
    # Call P&L service
    try:
        import requests
        response = requests.post('http://localhost:5002/pnl', json={"trade_id": trade_id, "symbol": symbol, "price": computed_price, "quantity": quantity}, headers={'X-Trace-Id': trace_id})
        if response.status_code == 200:
            logging.info("P&L service called successfully", extra={"trace_id": trace_id, "trade_id": trade_id})
        else:
            logging.warning("P&L service call failed", extra={"trace_id": trace_id, "trade_id": trade_id, "status_code": response.status_code})
    except Exception as e:
        logging.error("Error calling P&L service", extra={"trace_id": trace_id, "error": str(e)})
    
    return jsonify({"trade_id": trade_id, "computed_price": computed_price}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)