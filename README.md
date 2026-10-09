# API Shield — 3D Intelligent Rate Limiting & Abuse Prevention Gateway

[![API Shield CI](https://github.com/Yuvaraj-sudo-max/API-SHIELD/actions/workflows/ci.yml/badge.svg)](https://github.com/Yuvaraj-sudo-max/API-SHIELD/actions/workflows/ci.yml)
![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)
![Redis](https://img.shields.io/badge/redis-7.x-DC382D?logo=redis&logoColor=white)
![DeepSeek](https://img.shields.io/badge/AI-DeepSeek%20LLM-4f46e5)
![License](https://img.shields.io/badge/license-MIT-green)

API Shield is an enterprise-grade API gateway and rate-limiting system designed to protect modern microservices and LLM endpoints against traffic spikes, bot attacks, and volumetric API abuse. Featuring a **3D Three.js holographic command matrix**, deep integration with **DeepSeek AI**, multi-tenant client tiering, and native **Prometheus telemetry**, API Shield delivers high-throughput traffic shaping with zero external database dependencies when running in standalone mode.

---

## 🌟 Key Capabilities

- **3 Core Rate Limiting Algorithms**:
  - **Fixed Window** (`INCR` + TTL atomic counters for high-throughput simplicity).
  - **Sliding Window** (Redis `ZSET` precision sliding log preventing boundary bursts).
  - **Token Bucket** (Continuous fractional token refill with burst capacity control).
- **Multi-Tenant Client Tiering**:
  - Dynamically scales request allowances based on client tier (`Free`: 1.0x, `Pro`: 3.0x, `Enterprise`: 10.0x).
  - Injects `X-Client-Tier` headers and adapts quotas dynamically.
- **DeepSeek AI Security Copilot**:
  - **AI Rate-Limited LLM Gateway**: `/api/ai/chat` protected by sliding-window policies.
  - **Autonomous Threat Auditor**: Analyzes security audit streams to identify abusive traffic patterns.
  - **Policy Synthesis Copilot**: Generates structured rate limit policies from natural language intent.
- **Tiered Abuse Defense & Penalty Box**:
  - Progressively escalates block penalties for repeated violators (1st: 60s, 2nd: 300s, 3rd+: 1800s).
- **Prometheus Telemetry (`/metrics`)**:
  - Standard Prometheus exposition metrics for requests, rate limits, active policies, and AI completions.
- **Production Ready Containerization**:
  - High-performance Gunicorn WSGI server, multi-stage Docker container, and 1-command `docker-compose.yml`.

---

## 📁 Project Architecture

```
api_shield/
├── app.py                     # Flask application factory and server entrypoint
├── config.py                  # Environment config and automatic .env parser
├── routes.py                  # API endpoints, middleware, and Prometheus metrics
├── limiter.py                 # Fixed Window, Sliding Window, and Token Bucket engines
├── policy.py                  # RateLimitRule models and PolicyManager CRUD
├── identity.py                # Client identification, key masking, and tiering
├── metrics.py                 # Prometheus exposition metrics collector
├── blocking.py                # Abuse detection and tiered penalty blocking
├── logging_utils.py           # Request decision audit logging
├── ai_service.py              # DeepSeek AI gateway and copilot integration
├── policies.json              # Default policy catalog
├── postman_collection.json    # Complete Postman testing suite (16 requests)
├── Dockerfile                 # Multi-stage production container
├── docker-compose.yml         # API Shield + Redis cluster orchestrator
├── .dockerignore              # Clean container build rules
├── .github/workflows/ci.yml   # Multi-version Pytest matrix CI workflow
└── tests/                     # 46 Automated Unit & Integration Tests
```

---

## 🚀 Quick Start Guide

### Option A: Run with Docker Compose (Recommended)

Start API Shield and Redis together with a single command:

```bash
# 1. Clone repository
git clone https://github.com/Yuvaraj-sudo-max/API-SHIELD.git
cd API-SHIELD

# 2. Configure environment
cp .env.example .env
# Edit .env with your DEEPSEEK_API_KEY and API_KEY

# 3. Spin up cluster
docker-compose up --build -d
```
Access the dashboard at **`http://localhost:5000`** and metrics at **`http://localhost:5000/metrics`**.

---

### Option B: Local Python Environment

**Windows (PowerShell):**
```powershell
# 1. Navigate to directory
cd C:\Users\user\.gemini\antigravity-ide\scratch\api_shield

# 2. Activate Virtual Environment
.\venv\Scripts\Activate.ps1

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Run Application
python app.py
```

**Linux / macOS:**
```bash
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

The application will start on **`http://127.0.0.1:5000`**.

---

## 🧪 Running Automated Tests (46 Tests)

Run the full automated test suite with **pytest**:

```powershell
pytest -v
```

All 46 unit and integration test cases will execute:
- DeepSeek AI completions, masked key privacy, and prompt rate limiting.
- Sliding Window, Fixed Window, and Token Bucket burst calculations.
- Multi-tenant client tiering and multiplier scaling (`Free`, `Pro`, `Enterprise`).
- Progressive penalty blocking and automated cooldowns.
- Prometheus `/metrics` exposition format.

---

## 📊 Rate Limiting Algorithm Comparison

| Feature | Fixed Window | Sliding Window | Token Bucket |
| :--- | :--- | :--- | :--- |
| **Engine** | Redis Atomic Counter (`INCR`) | Redis Sorted Set (`ZSET`) | Redis Hash (`tokens`, `timestamp`) |
| **Boundary Burst Protection** | ❌ May burst 2x at boundary | ✅ 100% Guaranteed | ✅ Controlled burst up to capacity |
| **Memory Efficiency** | 🟢 Minimal (1 key per window) | 🟡 O(N) entries per window | 🟢 Minimal (1 hash per client) |
| **Best Used For** | Standard REST APIs | Sensitive Auth/Payments | Streaming / LLM Gateways |

---

## ⚙️ Core Concepts & Business Rules

### 1. Client Identification & Multi-Tenant Tiers (SRS Section 3.1)
1. Checks the `X-API-Key` HTTP header. If present, client is identified as `key:<api_key>`.
2. Otherwise, falls back to the client remote IP address (`ip:<remote_addr>`).
3. Evaluates client tier (`free`, `pro`, `enterprise`) from `X-Client-Tier` or key prefixes (`pro_`, `ent_`).
4. Sensitive keys are automatically masked before logging (e.g. `key:sk-fc0...b1df`).

### 2. Tiered Temporary Blocking (SRS Section 6.1)
When a client repeatedly exceeds limits, temporary penalty blocks escalate:
- **1st violation**: 60 seconds
- **2nd violation**: 300 seconds (5 minutes)
- **3rd+ violations**: 1800 seconds (30 minutes)

Subsequent requests from blocked clients return `HTTP 429 Too Many Requests` with a `Retry-After: <ttl>` header.

---

## 📡 API Endpoints Reference

### Public / Unprotected
- `GET /health` — Check system status and Redis connectivity.
- `GET /metrics` — Prometheus standard exposition format.
- `GET /` — 3D interactive command dashboard.

### Policy Management
- `GET /api/policies` — List all registered policies.
- `POST /api/policies` — Create a new rate limiting policy.
- `GET /api/policies/<name>` — Retrieve a specific policy.
- `PUT /api/policies/<name>` — Update an existing policy.
- `POST /api/policies/<name>/activate` — Activate policy.
- `POST /api/policies/<name>/deactivate` — Deactivate policy.
- `DELETE /api/policies/<name>` — Delete policy.

### Protected Endpoints
- `GET /api/products` — Fixed Window (5 req / 60s).
- `GET /api/users` — Sliding Window (10 req / 60s).
- `GET /api/stream` — Token Bucket (10 burst / 30s).
- `POST /api/login` — Auth Guard (5 req / 300s).
- `POST /api/ai/chat` — DeepSeek LLM Gateway (5 req / 60s).

### DeepSeek AI Security Endpoints
- `GET /api/ai/status` — Checks DeepSeek connection and masked key status.
- `POST /api/ai/chat` — Rate-limited AI completion endpoint.
- `POST /api/ai/analyze-threat` — Autonomous threat audit over recent traffic logs.
- `POST /api/ai/generate-policy` — Natural language policy generator powered by DeepSeek.

---

## 📈 Prometheus Telemetry

Scrape gateway metrics via standard Prometheus format at `GET /metrics`:

```
# HELP api_shield_requests_total Total number of HTTP requests processed
# TYPE api_shield_requests_total counter
api_shield_requests_total{endpoint="/api/ai/chat",status="200",tier="pro"} 14
api_shield_requests_total{endpoint="/api/stream",status="429",tier="free"} 2

# HELP api_shield_rate_limit_blocks_total Total rate limit rejections (HTTP 429)
# TYPE api_shield_rate_limit_blocks_total counter
api_shield_rate_limit_blocks_total{endpoint="/api/stream",algorithm="token_bucket"} 2

# HELP api_shield_policies_active Active rate limit policies
# TYPE api_shield_policies_active gauge
api_shield_policies_active 5
```

---

## 📜 Standard Response Headers

Every request processed by API Shield includes RFC-compliant rate limit telemetry:

| Header | Description |
| :--- | :--- |
| `X-RateLimit-Limit` | Effective request limit for the active window and client tier |
| `X-RateLimit-Remaining` | Remaining request quota in the active window |
| `X-Client-Tier` | Resolved client service tier (`free`, `pro`, `enterprise`) |
| `Retry-After` | Seconds until quota replenishes or penalty block expires (on HTTP 429) |

---

## 📬 Postman Testing Suite (16 Requests)

A pre-configured Postman collection is included in the project root:
- File: `postman_collection.json`

To use:
1. Open Postman.
2. Click **Import** and select `postman_collection.json`.
3. Pre-configured variables: `base_url` (`http://127.0.0.1:5000`), `api_key` (`sk-fc02e982d5934be9a510598120f2b1df`).

---

## 👤 Author & License

Created by **[Yuvaraj s (Yuvaraj-sudo-max)](https://github.com/Yuvaraj-sudo-max)**.  
Released under the **MIT License**.
