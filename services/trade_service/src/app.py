import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify
import uuid
import requests
from models import Trade

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/trade_service.log'),
        logging.StreamHandler()
    ]
)

# In-memory storage for trades
trades = {}

def create_trade_object(trade_id, symbol, quantity, price, trade_type):
    """Helper function to create a Trade object"""
    timestamp = datetime.now().isoformat()
    return Trade(
        trade_id=trade_id,
        symbol=symbol,
        quantity=quantity,
        price=price,
        trade_type=trade_type,
        timestamp=timestamp
    )

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "trade_service"})

@app.route('/trades', methods=['POST'])
def create_trade():
    trace_id = request.headers.get('X-Trace-Id', str(uuid.uuid4()))
    logging.info("Received trade creation request", extra={"trace_id": trace_id, "endpoint": "/trades", "method": "POST"})
    
    data = request.get_json()
    if not data:
        logging.error("Invalid JSON payload", extra={"trace_id": trace_id})
        return jsonify({"error": "Invalid JSON"}), 400
    
    trade_id = data.get('trade_id')
    symbol = data.get('symbol')
    quantity = data.get('quantity')
    price = data.get('price')
    trade_type = data.get('trade_type')
    
    if not all([trade_id, symbol, quantity, price, trade_type]):
        logging.error("Missing required fields", extra={"trace_id": trace_id, "fields": ["trade_id", "symbol", "quantity", "price", "trade_type"]})
        return jsonify({"error": "Missing required fields"}), 400
    
    trade = create_trade_object(trade_id, symbol, quantity, price, trade_type)
    trades[trade_id] = trade
    
    logging.info("Trade created successfully", extra={"trace_id": trace_id, "trade_id": trade_id, "symbol": symbol})
    
    # Call pricing service
    try:
        import requests
        response = requests.post('http://localhost:5001/prices', json={"trade_id": trade_id, "symbol": symbol, "quantity": quantity}, headers={'X-Trace-Id': trace_id})
        if response.status_code == 200:
            logging.info("Pricing service called successfully", extra={"trace_id": trace_id, "trade_id": trade_id})
        else:
            logging.warning("Pricing service call failed", extra={"trace_id": trace_id, "trade_id": trade_id, "status_code": response.status_code})
    except Exception as e:
        logging.error("Error calling pricing service", extra={"trace_id": trace_id, "error": str(e)})
    
    return jsonify({"message": "Trade created", "trade_id": trade_id}), 201

@app.route('/trades/<trade_id>', methods=['GET'])
def get_trade(trade_id):
    trace_id = request.headers.get('X-Trace-Id', str(uuid.uuid4()))
    logging.info("Fetching trade", extra={"trace_id": trace_id, "trade_id": trade_id})
    
    trade = trades.get(trade_id)
    if not trade:
        logging.warning("Trade not found", extra={"trace_id": trace_id, "trade_id": trade_id})
        return jsonify({"error": "Trade not found"}), 404
    
    return jsonify({
        "trade_id": trade.trade_id,
        "symbol": trade.symbol,
        "quantity": trade.quantity,
        "price": trade.price,
        "trade_type": trade.trade_type,
        "timestamp": trade.timestamp
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)