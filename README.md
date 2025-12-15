# Bank Microservices Ecosystem for GenAI Observability Demo

## 📋 Project Overview

This project simulates a **production-grade bank trading system** consisting of interconnected microservices that process trades, calculate prices, compute P&L (Profit & Loss), and assess risk levels. The primary goal is to demonstrate how **GenAI-powered observability** can help with:

- **Root Cause Analysis (RCA)**: Identifying why failures occurred across multiple services
- **Field Lineage Tracking**: Understanding how data fields are derived and transformed
- **Workflow Analysis**: Mapping the complete flow of requests across services

---

## 🏗️ Architecture & Services

### Service Overview

| Service | Port | Responsibility | Calls Next Service |
|---------|------|----------------|-------------------|
| **Trade Service** | 5000 | Ingests and validates trades | ✅ Pricing Service |
| **Pricing Service** | 5001 | Computes market-based prices | ✅ P&L Service |
| **P&L Service** | 5002 | Calculates Profit & Loss | ✅ Risk Service |
| **Risk Service** | 5003 | Assesses risk levels | ❌ (End of chain) |

### Data Flow & Interlinkage

```
User Request (Trade ID: 12345)
    ↓
[Trade Service] 
    - Validates trade data
    - Stores trade (symbol, quantity, price, type)
    - Generates trace_id: 123e4567-e89b-12d3-a456-426614174000
    - Logs: "Trade created successfully"
    ↓ HTTP POST with trace_id
[Pricing Service]
    - Receives: {trade_id, symbol, quantity}
    - Computes price using compute_price() function
    - Logs: "Price computed successfully" with computed_price
    ↓ HTTP POST with same trace_id
[P&L Service]
    - Receives: {trade_id, symbol, price, quantity}
    - Calculates: pnl_value = (price - cost) * quantity
    - Logs: "P&L computed successfully" with pnl_value
    ↓ HTTP POST with same trace_id
[Risk Service]
    - Receives: {trade_id, pnl_value, quantity}
    - Assesses risk using assess_risk() function
    - Logic: if pnl < 0 and quantity > 50 → HIGH risk
    - Logs: "Risk assessed successfully" with risk_level
```

**Key Design Features:**
- **Trace ID Propagation**: Every request carries a `X-Trace-Id` header that flows through all services
- **Structured JSON Logging**: All logs are JSON-formatted with timestamp, service, trace_id, and contextual data
- **Realistic Failures**: Services simulate timeouts, data errors, and external dependencies
- **Data Transformation**: Each service enriches/transforms data (trade → price → pnl → risk)

### Technology Stack

- **Framework**: Flask (REST APIs)
- **Logging**: Python logging with JSON formatters (Splunk-compatible)
- **Containerization**: Docker + Docker Compose
- **Testing**: pytest
- **Models**: Python dataclasses for type safety

---

## 🔍 Sample User Queries & Solutions

### Query 1: Root Cause Analysis (RCA)
**User Query:** *"Why did the P&L calculation fail for trade ID 12345? What was the sequence of events?"*

**How to Answer Using This System:**

1. **Search Splunk Logs** for `trade_id: "12345"`:
   ```json
   {"timestamp": "2025-12-15T10:00:00Z", "service": "trade_service", "trace_id": "...174000", "message": "Trade created successfully", "extra": {"trade_id": "12345"}}
   {"timestamp": "2025-12-15T10:00:03Z", "service": "pricing_service", "trace_id": "...174000", "message": "Price computed successfully", "extra": {"trade_id": "12345", "computed_price": 148.5}}
   {"timestamp": "2025-12-15T10:00:05Z", "service": "pnl_service", "trace_id": "...174000", "message": "P&L computed successfully", "extra": {"trade_id": "12345", "pnl_value": 85.0}}
   ```

2. **Trace the Flow** using `trace_id: ...174000`:
   - Trade Service → SUCCESS (created trade)
   - Pricing Service → SUCCESS (computed price: 148.5)
   - P&L Service → SUCCESS (computed P&L: 85.0)

3. **For Failure Scenario** (if trade 99999 failed):
   ```json
   {"timestamp": "2025-12-15T10:01:03Z", "service": "pnl_service", "trace_id": "...174003", "message": "P&L computation failed due to data inconsistency", "extra": {"trade_id": "99999"}}
   ```

4. **Code Analysis** - Examine `pnl_service/src/app.py`:
   - Function: `compute_pnl()`
   - Line with failure: Random failure simulation `if random.random() < 0.05`
   - Root cause: 5% chance of data inconsistency error

**GenAI Agent Answer:**
> "The P&L calculation for trade ID 12345 succeeded with value 85.0. However, for trade 99999, the failure occurred at 10:01:03 in the P&L service due to a 'data inconsistency' error (HTTP 500). Analyzing the code in `pnl_service/src/app.py:46`, the system simulates occasional failures (5% chance) to mimic external data issues. The sequence: Trade Service → Pricing Service (timeout occurred) → P&L Service (aborted due to missing price data). Recommendation: Add retry logic and validate upstream dependencies."

---

### Query 2: Field Lineage Tracking
**User Query:** *"How was the 'pnl_value' field derived in the P&L service? Which functions were involved?"*

**How to Answer:**

1. **Parse Code** using AST:
   - File: `pnl_service/src/app.py`
   - Function: `compute_pnl()`
   - Variables extracted:
     ```python
     price = data.get('price')          # From Pricing Service
     quantity = data.get('quantity')    # From Trade Service
     cost = base_costs.get(symbol, 90.0)  # From internal lookup
     pnl_value = (price - cost) * quantity  # Computation
     ```

2. **Build Lineage Graph**:
   ```
   Trade Service (quantity) ──┐
                              ├──→ P&L Service (compute_pnl)
   Pricing Service (price) ───┤        ↓
                              └──→ pnl_value = (price - cost) * quantity
   ```

3. **Trace Logs for Values**:
   ```json
   {"service": "trade_service", "extra": {"quantity": 10}}
   {"service": "pricing_service", "extra": {"computed_price": 148.5}}
   {"service": "pnl_service", "extra": {"pnl_value": 85.0, "cost": 140.0}}
   ```

**GenAI Agent Answer:**
> "The field 'pnl_value' is computed in the P&L service (`pnl_service/src/app.py:46`) within the `compute_pnl()` function. The calculation is: `pnl_value = (price - cost) * quantity`.
>
> **Data Lineage:**
> - `price`: Received from Pricing Service (computed via `compute_price()` function)
> - `cost`: Retrieved from internal `base_costs` dictionary (line 43)
> - `quantity`: Originated from Trade Service, passed through Pricing Service
>
> For trade 12345: pnl_value = (148.5 - 140.0) * 10 = 85.0"

---

### Query 3: Workflow Analysis
**User Query:** *"Explain the complete workflow for processing a trade from ingestion to risk assessment."*

**How to Answer:**

1. **Extract Service Call Chain** from code:
   - Trade Service → `requests.post('http://localhost:5001/prices')`
   - Pricing Service → `requests.post('http://localhost:5002/pnl')`
   - P&L Service → `requests.post('http://localhost:5003/risk')`

2. **Map Functions**:
   - `trade_service/app.py:create_trade()` → Validates input
   - `pricing_service/app.py:compute_trade_price()` → Calls `compute_price(symbol)`
   - `pnl_service/app.py:compute_pnl()` → Calculates P&L
   - `risk_service/app.py:assess_trade_risk()` → Calls `assess_risk(pnl, quantity)`

3. **Follow Trace ID** in logs:
   ```
   10:00:00 [trade_service] Trade created successfully
   10:00:02 [pricing_service] Price computed successfully
   10:00:04 [pnl_service] P&L computed successfully
   10:00:06 [risk_service] Risk assessed successfully
   ```

**GenAI Agent Answer:**
> "**Complete Trade Processing Workflow:**
>
> **Step 1: Trade Ingestion** (Trade Service)
> - Endpoint: POST /trades
> - Function: `create_trade()`
> - Validates: trade_id, symbol, quantity, price, trade_type
> - Action: Stores trade, generates trace_id
>
> **Step 2: Price Computation** (Pricing Service)
> - Endpoint: POST /prices
> - Function: `compute_trade_price()` → `compute_price(symbol)`
> - Logic: Fetches base price for symbol (AAPL=150, GOOGL=2800) + random variance
> - Output: computed_price
>
> **Step 3: P&L Calculation** (P&L Service)
> - Endpoint: POST /pnl
> - Function: `compute_pnl()`
> - Formula: pnl_value = (computed_price - base_cost) × quantity
> - Output: pnl_value
>
> **Step 4: Risk Assessment** (Risk Service)
> - Endpoint: POST /risk
> - Function: `assess_trade_risk()` → `assess_risk(pnl, quantity)`
> - Logic: HIGH if pnl < 0 AND quantity > 50; MEDIUM if pnl < -100; else LOW
> - Output: risk_level
>
> **Duration**: Typical flow takes 6-10 seconds. Trace ID enables end-to-end tracking."

---

### Query 4: Multi-Service RCA with Downstream Impact
**User Query:** *"What caused the pricing service to timeout for trade ID 67890? Did it affect downstream services?"*

**How to Answer:**

1. **Search Logs** for trade 67890:
   ```json
   {"timestamp": "2025-12-15T10:00:11Z", "service": "trade_service", "trace_id": "...174002", "message": "Trade created successfully", "extra": {"trade_id": "67890"}}
   {"timestamp": "2025-12-15T10:00:12Z", "service": "trade_service", "trace_id": "...174002", "message": "Error calling pricing service", "extra": {"error": "Connection refused"}}
   {"timestamp": "2025-12-15T10:00:17Z", "service": "pricing_service", "trace_id": "...174002", "message": "Price computation timed out", "extra": {"trade_id": "67890"}}
   ```

2. **Analyze Code** - `pricing_service/app.py:51`:
   ```python
   if random.random() < 0.1:  # 10% chance
       time.sleep(5)  # Timeout
       logging.error("Price computation timed out", ...)
       return jsonify({"error": "Timeout"}), 504
   ```

3. **Check Downstream Impact**:
   - No logs from P&L or Risk services for trace ...174002
   - Trade Service received error response

**GenAI Agent Answer:**
> "**Root Cause:** The Pricing Service timed out for trade 67890 (trace_id: ...174002) at 10:00:17. 
>
> **Technical Details:**
> - Function: `compute_trade_price()` in `pricing_service/src/app.py`
> - Issue: Simulated timeout (10% probability) - line 51 executes `time.sleep(5)` before returning 504 error
> - Duration: 5-second delay before timeout
>
> **Downstream Impact:**
> - **P&L Service**: NOT called (no log entries for this trace_id)
> - **Risk Service**: NOT called (chain broken)
> - **Trade Service**: Received error but logged the trade successfully
>
> **Business Impact:** Trade 67890 is recorded but has no price, P&L, or risk assessment. Requires manual review.
>
> **Recommendation:** Implement circuit breaker pattern and async retry for pricing failures."

---

### Query 5: Advanced Field Lineage
**User Query:** *"Trace how the 'risk_level' in the Risk service is calculated from trade data."*

**How to Answer:**

1. **Full Data Flow**:
   ```
   Trade Service:
     Input: {trade_id, symbol, quantity, price, trade_type}
     Output: {trade_id, symbol, quantity}
     
   Pricing Service:
     Input: {trade_id, symbol, quantity}
     Function: compute_price(symbol) → base_prices[symbol] + random(-5, 5)
     Output: {trade_id, computed_price}
     
   P&L Service:
     Input: {trade_id, symbol, price, quantity}
     Function: pnl_value = (price - base_costs[symbol]) * quantity
     Output: {trade_id, pnl_value, quantity}
     
   Risk Service:
     Input: {trade_id, pnl_value, quantity}
     Function: assess_risk(pnl_value, quantity)
     Logic:
       - if pnl_value < 0 AND quantity > 50 → "HIGH"
       - elif pnl_value < -100 → "MEDIUM"
       - else → "LOW"
     Output: {trade_id, risk_level}
   ```

2. **Code References**:
   - Trade data origin: `trade_service/app.py:create_trade()`
   - Price computation: `pricing_service/app.py:compute_price()` (line 19)
   - P&L calculation: `pnl_service/app.py:compute_pnl()` (line 46)
   - Risk logic: `risk_service/app.py:assess_risk()` (line 18)

**GenAI Agent Answer:**
> "**Field Lineage for 'risk_level':**
>
> **Origin → Transformation → Final Value**
>
> 1. **Trade Service** (`trade_service/src/app.py:32`)
>    - User provides: `quantity = 10`, `symbol = "AAPL"`
>
> 2. **Pricing Service** (`pricing_service/src/app.py:19-23`)
>    - Function: `compute_price(symbol)`
>    - Computation: `base_prices["AAPL"] (150.0) + random(-5, 5) = 148.5`
>    - Field created: `computed_price = 148.5`
>
> 3. **P&L Service** (`pnl_service/src/app.py:46`)
>    - Receives: `price=148.5`, `quantity=10`
>    - Looks up: `cost = base_costs["AAPL"] = 140.0`
>    - Computation: `pnl_value = (148.5 - 140.0) * 10 = 85.0`
>    - Field created: `pnl_value = 85.0`
>
> 4. **Risk Service** (`risk_service/src/app.py:18-24`)
>    - Receives: `pnl_value=85.0`, `quantity=10`
>    - Function: `assess_risk(85.0, 10)`
>    - Logic evaluation:
>      - Is `85.0 < 0 AND 10 > 50`? No
>      - Is `85.0 < -100`? No
>      - Default: return "LOW"
>    - **Final Field**: `risk_level = "LOW"`
>
> **Summary:** risk_level is derived from original trade quantity and calculated P&L, which itself depends on the price computation chain."

---

### Query 6: Complex Multi-Service Query
**User Query:** *"Show all services involved in a trade with negative P&L and high risk."*

**How to Answer:**

1. **Filter Logs** for negative P&L:
   ```json
   {"service": "pnl_service", "extra": {"trade_id": "11111", "pnl_value": -150.0}}
   ```

2. **Find Associated Risk**:
   ```json
   {"service": "risk_service", "extra": {"trade_id": "11111", "risk_level": "HIGH"}}
   ```

3. **Trace Backwards** using trace_id `...174004`:
   ```json
   {"service": "trade_service", "trace_id": "...174004", "extra": {"trade_id": "11111", "symbol": "AAPL", "quantity": 100}}
   {"service": "pricing_service", "trace_id": "...174004", "extra": {"trade_id": "11111", "computed_price": 138.0}}
   {"service": "pnl_service", "trace_id": "...174004", "extra": {"trade_id": "11111", "pnl_value": -150.0}}
   {"service": "risk_service", "trace_id": "...174004", "extra": {"trade_id": "11111", "risk_level": "HIGH"}}
   ```

**GenAI Agent Answer:**
> "**Trade 11111 Analysis (Negative P&L + High Risk):**
>
> **All Services Involved:**
>
> | Service | Action | Result | Timestamp |
> |---------|--------|--------|-----------|
> | Trade Service | Ingested trade | symbol: AAPL, quantity: 100 | 10:01:10 |
> | Pricing Service | Computed price | computed_price: 138.0 | 10:01:11 |
> | P&L Service | Calculated P&L | pnl_value: -150.0 (LOSS) | 10:01:11 |
> | Risk Service | Assessed risk | risk_level: HIGH | 10:01:12 |
>
> **Why High Risk?**
> - P&L is negative (-150.0)
> - Quantity is large (100 units)
> - Risk logic (`risk_service/app.py:18`): `if pnl < 0 AND quantity > 50 → HIGH`
>
> **Business Context:**
> - Cost basis: $140/share (base_costs["AAPL"])
> - Actual price: $138/share (computed)
> - Loss per unit: $2
> - Total loss: $2 × 100 = -$200... wait, log shows -$150
> - Calculation: (138 - 140) * 100 = -200 (discrepancy in logs - potential bug!)
>
> **Action Required:** Alert risk management team. Consider position liquidation."

---

## 🚀 Running the Services

### With Docker Compose (Recommended)

```bash
docker-compose up --build
```

This will start all services with proper networking.

### Locally

For each service:

```bash
cd services/trade_service
pip install -r requirements.txt
python src/app.py
```

Repeat for other services (ports 5001, 5002, 5003).

---

## 📊 Logs

Logs are written to `services/<service>/logs/<service>.log` in JSON format, suitable for Splunk ingestion. Sample logs are provided for all services with:
- Successful trade flows (trade 12345)
- Timeout scenarios (trade 67890)
- Failed P&L calculations (trade 99999)
- High-risk trades (trade 11111)

**Log Format:**
```json
{
  "timestamp": "2025-12-15T10:00:00Z",
  "level": "INFO",
  "service": "trade_service",
  "trace_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Trade created successfully",
  "extra": {
    "trade_id": "12345",
    "symbol": "AAPL"
  }
}
```

---

## 🧪 Testing

Run tests for a service:

```bash
cd services/trade_service
pip install -r requirements-dev.txt
pytest
```

---

## 📚 Next Steps for GenAI Observability Platform

1. **Code Analysis**: Parse all Python files using AST to extract functions, classes, variables
2. **Knowledge Graph**: Store entities (services, functions, fields) and relationships in a graph database
3. **Log Ingestion**: Set up Splunk forwarder to ingest logs from all services
4. **LLM Summarization**: Generate function-level summaries for each service
5. **Embeddings**: Create vector embeddings for semantic search
6. **RAG Agent**: Build agent with tools for log search, code search, and graph traversal
7. **Multi-turn Chat**: Implement conversational interface for production support teams