# PayOps Copilot

AI-powered payments ops copilot. Ingests Razorpay webhooks + bank CSVs, detects settlement mismatches and chargeback deadlines, runs AI agents (Gemini primary, Claude fallback) to produce root cause + resolution steps, serves a React ops dashboard with approve/reject HITL flow.

---

## Quick Start (Two Terminals)

### Prerequisites

- Anaconda (or Miniconda) installed
- Node.js (installed by environment.yml via conda-forge)
- A **Gemini API key** (free at https://aistudio.google.com/apikey) — OR an Anthropic key

---

### Step 1 — Create conda environment

```bash
conda env create -f environment.yml
conda activate payops-copilot
```

### Step 2 — Install Python packages

```bash
cd backend
pip install -r requirements.txt
```

### Step 3 — Set your API key

`backend/.env` is pre-created. Edit it to add your Gemini key:

```
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.0-flash
DATABASE_URL=sqlite+aiosqlite:///./payops.db
FRONTEND_URL=http://localhost:5173
```

> The app prefers `GEMINI_API_KEY`. If it's empty, it falls back to `ANTHROPIC_API_KEY`.
> Without either key, all other features work; only the **Analyze** button returns a 400.

### Step 4 — Seed the database

```bash
cd backend
python seeds/seed.py
```

Expected output:
```
  Inserted 15 payments
  Inserted 13 settlements
  Inserted 13 bank entries
  Inserted 3 refunds (refund_002 + refund_003 are duplicates)
  Inserted 2 chargebacks

Seed complete. Cases created: 5
  [MISSING_SETTLEMENT] id=1 priority=92
  [MISSING_SETTLEMENT] id=2 priority=92
  [AMOUNT_MISMATCH] id=3 priority=88
  [DUPLICATE_REFUND] id=4 priority=100
  [CHARGEBACK_RISK] id=5 priority=100
```

### Step 5 — Run backend (Terminal 1)

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API: http://localhost:8000  
Swagger: http://localhost:8000/docs

### Step 6 — Run frontend (Terminal 2)

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

Expected: **11 tests pass**

```
tests/test_matcher.py::test_missing_settlement_detected          PASSED
tests/test_matcher.py::test_no_false_positive_when_settled       PASSED
tests/test_matcher.py::test_amount_mismatch_detected             PASSED
tests/test_matcher.py::test_duplicate_refund_detected            PASSED
tests/test_recon_agent.py::test_confidence_parsing               PASSED
tests/test_recon_agent.py::test_confidence_clamp                 PASSED
tests/test_recon_agent.py::test_confidence_missing               PASSED
tests/test_recon_agent.py::test_confidence_zero                  PASSED
tests/test_recon_agent.py::test_agent_result_structure           PASSED
tests/test_dispute_agent.py::test_deadline_critical_prefix       PASSED
tests/test_dispute_agent.py::test_priority_score_100_for_urgent  PASSED
```

---

## Testing Webhook Ingestion

```bash
curl -X POST http://localhost:8000/webhooks/razorpay \
  -H "Content-Type: application/json" \
  -d '{
    "event": "payment.captured",
    "payload": {
      "payment": {
        "entity": {
          "id": "pay_webhook_001",
          "order_id": "order_wh_001",
          "merchant_id": "merchant_001",
          "amount": 50000,
          "currency": "INR",
          "status": "captured",
          "method": "upi"
        }
      }
    }
  }'
```

## Testing Analytics

```bash
curl http://localhost:8000/analytics/dashboard
```

---

## AI Provider Configuration

The agent layer is **provider-agnostic**:

| Priority | Provider | Environment Variable | Notes |
|----------|----------|---------------------|-------|
| 1st | **Gemini** | `GEMINI_API_KEY` | Free tier at aistudio.google.com |
| 2nd | **Anthropic** | `ANTHROPIC_API_KEY` | Paid — Claude Sonnet |
| None | Graceful degradation | — | All features work except Analyze |

The active provider is auto-detected at startup. No code changes needed to switch.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/webhooks/razorpay` | Ingest Razorpay webhook |
| POST | `/ingest/bank-statement` | Upload bank CSV |
| GET | `/cases` | List cases (paginated, filterable by status) |
| GET | `/cases/{id}` | Case detail with payment + audit log |
| POST | `/cases/{id}/analyze` | Run AI agent analysis |
| POST | `/cases/{id}/approve` | Approve resolution (HITL) |
| POST | `/cases/{id}/reject` | Reject AI analysis (HITL) |
| GET | `/disputes` | Open chargebacks by deadline |
| GET | `/analytics/dashboard` | Dashboard metrics |

---

## Architecture

```
Razorpay Webhook → FastAPI → SQLite
                               ↓
                         Matching Engine
                         ├── MISSING_SETTLEMENT (>72h captured, no link)
                         ├── AMOUNT_MISMATCH (bank vs settlement UTR diff)
                         ├── DUPLICATE_REFUND (2+ processed refunds)
                         └── CHARGEBACK_RISK (respond_by ≤ 48h)
                               ↓
                         ReconCase created
                               ↓
                         POST /cases/{id}/analyze
                               ↓
                    ┌──────────────────────────┐
                    │  Provider-Agnostic Agent  │
                    │  Gemini (primary)         │
                    │  Anthropic (fallback)     │
                    └──────────────────────────┘
                               ↓
                         pending_approval → HITL → manually_resolved
```
