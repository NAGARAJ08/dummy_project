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
file_handler = logging.FileHandler('logs/risk_service.log')
formatter = logging.Formatter('{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "risk_service", "trace_id": "%(trace_id)s", "message": "%(message)s", "extra": %(extra)s}')
handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(file_handler)

# In-memory risk assessments
risks = {}

def assess_risk(pnl_value, quantity):
    # Mock risk: High if P&L negative and quantity large
    if pnl_value < 0 and quantity > 50:
        return "HIGH"
    elif pnl_value < -100:
        return "MEDIUM"
    else:
        return "LOW"

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "risk_service"})

@app.route('/risk', methods=['POST'])
def assess_trade_risk():
    trace_id = request.headers.get('X-Trace-Id', str(uuid.uuid4()))
    logging.info("Received risk assessment request", extra={"trace_id": trace_id, "endpoint": "/risk", "method": "POST"})
    
    data = request.get_json()
    if not data:
        logging.error("Invalid JSON payload", extra={"trace_id": trace_id})
        return jsonify({"error": "Invalid JSON"}), 400
    
    trade_id = data.get('trade_id')
    pnl_value = data.get('pnl_value')
    quantity = data.get('quantity')
    
    if not all([trade_id, pnl_value is not None, quantity is not None]):
        logging.error("Missing required fields", extra={"trace_id": trace_id, "fields": ["trade_id", "pnl_value", "quantity"]})
        return jsonify({"error": "Missing required fields"}), 400
    
    risk_level = assess_risk(pnl_value, quantity)
    
    # Simulate occasional failure
    if random.random() < 0.03:  # 3% chance
        logging.error("Risk assessment failed due to external data unavailability", extra={"trace_id": trace_id, "trade_id": trade_id})
        return jsonify({"error": "External data unavailability"}), 503
    
    risks[trade_id] = {"risk_level": risk_level, "pnl_value": pnl_value, "quantity": quantity}
    
    logging.info("Risk assessed successfully", extra={"trace_id": trace_id, "trade_id": trade_id, "risk_level": risk_level})
    
    return jsonify({"trade_id": trade_id, "risk_level": risk_level}), 200

@app.route('/risk/<trade_id>', methods=['GET'])
def get_risk(trade_id):
    trace_id = request.headers.get('X-Trace-Id', str(uuid.uuid4()))
    logging.info("Fetching risk assessment", extra={"trace_id": trace_id, "trade_id": trade_id})
    
    risk = risks.get(trade_id)
    if not risk:
        logging.warning("Risk assessment not found", extra={"trace_id": trace_id, "trade_id": trade_id})
        return jsonify({"error": "Risk assessment not found"}), 404
    
    return jsonify(risk)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)