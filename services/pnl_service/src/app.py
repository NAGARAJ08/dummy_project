import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify
import uuid
import random

app = Flask(__name__)

# Configure JSON logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
file_handler = logging.FileHandler('logs/pnl_service.log')
formatter = logging.Formatter('{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "pnl_service", "trace_id": "%(trace_id)s", "message": "%(message)s", "extra": %(extra)s}')
handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(file_handler)

# In-memory P&L storage
pnls = {}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "pnl_service"})

@app.route('/pnl', methods=['POST'])
def compute_pnl():
    trace_id = request.headers.get('X-Trace-Id', str(uuid.uuid4()))
    logging.info("Received P&L computation request", extra={"trace_id": trace_id, "endpoint": "/pnl", "method": "POST"})
    
    data = request.get_json()
    if not data:
        logging.error("Invalid JSON payload", extra={"trace_id": trace_id})
        return jsonify({"error": "Invalid JSON"}), 400
    
    trade_id = data.get('trade_id')
    symbol = data.get('symbol')
    price = data.get('price')
    quantity = data.get('quantity')
    
    if not all([trade_id, symbol, price, quantity]):
        logging.error("Missing required fields", extra={"trace_id": trace_id, "fields": ["trade_id", "symbol", "price", "quantity"]})
        return jsonify({"error": "Missing required fields"}), 400
    
    # Mock P&L calculation: P&L = (price - cost) * quantity
    # Assume cost is some base price
    base_costs = {"AAPL": 140.0, "GOOGL": 2700.0, "MSFT": 280.0}
    cost = base_costs.get(symbol, 90.0)
    pnl_value = (price - cost) * quantity
    
    # Simulate occasional failure
    if random.random() < 0.05:  # 5% chance
        logging.error("P&L computation failed due to data inconsistency", extra={"trace_id": trace_id, "trade_id": trade_id})
        return jsonify({"error": "Data inconsistency"}), 500
    
    pnls[trade_id] = {"pnl_value": pnl_value, "symbol": symbol, "price": price, "quantity": quantity, "cost": cost}
    
    logging.info("P&L computed successfully", extra={"trace_id": trace_id, "trade_id": trade_id, "pnl_value": pnl_value})
    
    # Call Risk service
    try:
        import requests
        response = requests.post('http://localhost:5003/risk', json={"trade_id": trade_id, "pnl_value": pnl_value, "quantity": quantity}, headers={'X-Trace-Id': trace_id})
        if response.status_code == 200:
            logging.info("Risk service called successfully", extra={"trace_id": trace_id, "trade_id": trade_id})
        else:
            logging.warning("Risk service call failed", extra={"trace_id": trace_id, "trade_id": trade_id, "status_code": response.status_code})
    except Exception as e:
        logging.error("Error calling Risk service", extra={"trace_id": trace_id, "error": str(e)})
    
    return jsonify({"trade_id": trade_id, "pnl_value": pnl_value}), 200

@app.route('/pnl/<trade_id>', methods=['GET'])
def get_pnl(trade_id):
    trace_id = request.headers.get('X-Trace-Id', str(uuid.uuid4()))
    logging.info("Fetching P&L", extra={"trace_id": trace_id, "trade_id": trade_id})
    
    pnl = pnls.get(trade_id)
    if not pnl:
        logging.warning("P&L not found", extra={"trace_id": trace_id, "trade_id": trade_id})
        return jsonify({"error": "P&L not found"}), 404
    
    return jsonify(pnl)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)