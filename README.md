# API Shield — Simple API Rate Limiting System

API Shield is a modular Python & Flask API protection gateway that monitors and controls client request volume across protected endpoints. It prevents excessive requests, unintentional denial-of-service, brute-force login attempts, and simple API abuse using **Redis** storage, **Fixed Window** and **Sliding Window** rate-limiting algorithms, and an automated **tiered temporary blocking** mechanism.

---

## 📁 Project Architecture & Structure

```
api_shield/
│
├── app.py                  # Application factory and server bootstrap
├── config.py               # Environment configuration settings
├── routes.py               # API route definitions and rate-limiting middleware
├── identity.py             # Client identification (API key / IP) & masking
├── policy.py               # RateLimitRule model and PolicyManager CRUD
├── limiter.py              # Fixed and Sliding window algorithms
├── redis_store.py          # Redis client abstraction with automatic FakeRedis fallback
├── blocking.py             # BlockManager with tiered temporary blocking logic
├── logging_utils.py        # Request decision logging with masked client IDs
├── requirements.txt        # Python dependency manifest
├── policies.json           # Default policy configuration file
├── postman_collection.json # Ready-to-import Postman testing collection
├── README.md               # Documentation and local setup instructions
│
└── tests/
    ├── conftest.py         # Pytest fixtures and test application setup
    ├── test_limiter.py     # Unit tests for Fixed and Sliding window algorithms
    ├── test_policy.py      # Unit tests for Policy models, validation, and rules
    ├── test_identity.py    # Unit tests for client identification and key masking
    ├── test_blocking.py    # Unit tests for abuse prevention and block durations
    └── test_api_integration.py # End-to-end integration tests for Flask API
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Optional: Redis Server running on `localhost:6379`. If Redis is not running, API Shield automatically falls back to an in-memory `FakeRedis` backend so the application and tests run immediately without extra setup.

### 2. Activate the Virtual Environment
Always activate the project virtual environment before running commands:

**On Windows (PowerShell):**
```powershell
# Navigate to the project directory
cd C:\Users\user\.gemini\antigravity-ide\scratch\api_shield

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**On Linux / macOS:**
```bash
source venv/bin/activate
```

*(If you ever need to recreate the virtual environment from scratch:)*
```bash
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

### 3. Run the Application
Start the Flask development server using the virtual environment's Python:

```powershell
.\venv\Scripts\python app.py
```
Or with the virtual environment activated:
```bash
python app.py
```

The application will start on `http://127.0.0.1:5000`.

---

## 🧪 Running Automated Tests

Run the complete test suite with **pytest**:

```powershell
.\venv\Scripts\pytest -v
```

All 31 unit and integration test cases will execute against the in-memory test Redis fixture:
- Rate limiter tests (Fixed Window, Sliding Window, boundary crossing, counter isolation)
- Policy validation & lifecycle tests (CRUD, active/inactive states)
- Client identity & API key masking tests
- Abuse prevention & temporary blocking tiers
- End-to-end API integration tests

---

## ⚙️ Core Concepts & Business Rules

### 1. Client Identification (SRS Section 3.1)
1. Checks the `X-API-Key` HTTP header. If present and non-empty, client is identified as `key:<api_key>`.
2. Otherwise, falls back to the client remote IP address (`ip:<remote_addr>`).
3. For security and compliance (SRS Section 12), all sensitive API keys are masked before logging (e.g. `key:sec***56`).

### 2. Rate Limiting Algorithms (SRS Section 4)
- **Fixed Window (`fixed_window`)**: Divides time into fixed epoch buckets (`time // window`). Increments an atomic Redis key `rate:<key>:<window_num>` with a TTL equal to the window length.
- **Sliding Window (`sliding_window`)**: Tracks request timestamps in a Redis Sorted Set (`slide:<key>`). Prunes entries older than `now - window` using `ZREMRANGEBYSCORE`, records the new timestamp, and verifies the cardinal count using `ZCARD`.

### 3. Tiered Temporary Blocking (SRS Section 6.1)
When a client exceeds the limit, a violation is recorded (`violation:<client_id>`). Repeated violations trigger temporary blocking:
- **1–3 violations**: 5 minutes (300 seconds)
- **4–6 violations**: 15 minutes (900 seconds)
- **7+ violations**: 30 minutes (1800 seconds)

Subsequent requests from blocked clients immediately return `HTTP 429 Too Many Requests` with a `Retry-After: <ttl>` header.

---

## 📡 API Endpoints Reference

### Public / Unprotected
- `GET /health` — Check system status and Redis connectivity.
- `GET /` — Interactive live test dashboard.

### Policy Management
- `GET /api/policies` — List all registered policies.
- `POST /api/policies` — Create a new rate limiting policy.
- `GET /api/policies/<name>` — Retrieve a specific policy.
- `PUT /api/policies/<name>` — Update an existing policy.
- `POST /api/policies/<name>/activate` — Activate policy.
- `POST /api/policies/<name>/deactivate` — Deactivate policy.

### Protected Endpoints
- `GET /api/products` — Default: Fixed Window (limit: 5 requests / 60 seconds).
- `GET /api/users` — Default: Sliding Window (limit: 10 requests / 60 seconds).
- `POST /api/login` — Default: Fixed Window (limit: 5 requests / 300 seconds).
- `POST /api/ai/chat` — Default: Sliding Window (limit: 5 requests / 60 seconds). Protected DeepSeek AI Gateway.

### DeepSeek AI Integration Endpoints
- `GET /api/ai/status` — Checks DeepSeek API key connection, model, and account balance.
- `POST /api/ai/chat` — Rate-limited AI completion endpoint. Demonstrates API Shield protecting upstream LLM tokens against quota depletion.
- `POST /api/ai/analyze-threat` — Autonomous threat audit over recent traffic logs using DeepSeek intelligence.
- `POST /api/ai/generate-policy` — Natural language policy generator powered by DeepSeek.

### Sample Request Headers
```http
POST /api/ai/chat HTTP/1.1
Host: 127.0.0.1:5000
Content-Type: application/json
X-API-Key: sk-fc02e982d5934be9a510598120f2b1df

{
  "prompt": "Explain how rate limiting protects AI LLM endpoints."
}
```

### Sample Response Headers
```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 4
Content-Type: application/json
```

---

## 🔑 Environment Variables (.env)

The project includes automated `.env` file loading (`python-dotenv` with fallback):

| Variable | Description | Default |
|---|---|---|
| `API_KEY` | Primary API Key for testing client requests | `sk-fc02e982d5934be9a510598120f2b1df` |
| `DEEPSEEK_API_KEY` | DeepSeek LLM API Key | `sk-fc02e982d5934be9a510598120f2b1df` |
| `DEEPSEEK_BASE_URL` | DeepSeek API Base URL | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | Default model for completions | `deepseek-flash` |
| `APP_PORT` | Flask Gateway server port | `5000` |
| `REDIS_HOST` | Redis Host | `localhost` |
| `REDIS_PORT` | Redis Port | `6379` |

---

## 📬 Postman Testing

A pre-configured Postman collection is included in the project root:
- File: [postman_collection.json](file:///C:/Users/user/.gemini/antigravity-ide/scratch/api_shield/postman_collection.json)

To use:
1. Open Postman.
2. Click **Import** and select `postman_collection.json`.
3. The collection includes pre-built requests for all protected routes (including DeepSeek AI Gateway and Threat Analysis), with pre-configured variables for `base_url` (`http://127.0.0.1:5000`) and `api_key` (`sk-fc02e982d5934be9a510598120f2b1df`).
