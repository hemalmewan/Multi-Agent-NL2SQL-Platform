# Medicore — AI-Powered Medical Analytics Dashboard

> **Ask your hospital database anything in plain English. Get instant charts, tables, and AI insights.**

Medicore is a production-ready, full-stack medical analytics platform that combines a **multi-agent NL2SQL backend** (FastAPI + Python) with a **modern React dashboard** (Vite + Tailwind CSS + Plotly.js). Designed for doctors, hospital administrators, and data analysts who need data-driven insights without writing a single line of SQL.

---

## Table of Contents

- [Live Demo](#live-demo)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [API Reference](#api-reference)
- [Agent Pipeline](#agent-pipeline)
- [Database Schema](#database-schema)
- [Configuration](#configuration)
- [Screenshots](#screenshots)
- [Developer](#developer)

---

## Features

| Feature | Description |
|---|---|
| **Natural Language Queries** | Ask questions like "Show top 5 doctors by patient count" — no SQL needed |
| **Auto Chart Generation** | Bar, line, and pie charts selected and rendered automatically with Plotly.js |
| **AI Insights** | LLM-generated 2–3 sentence narrative for every chart |
| **Ambiguity Handling** | Unclear queries trigger a friendly refinement modal |
| **Pre-built Analytics** | 4 always-on charts: Revenue Trends, Doctor Workload, Top Diagnoses, Payment Methods |
| **Dark Mode** | Full light/dark theme with persistence |
| **Usage Tracking** | Settings page tracks tokens, cost, latency per query |
| **Export** | Download charts as PNG and table results as CSV |
| **SQL Safety** | 4-stage guardrails block all non-SELECT queries |
| **Observability** | Langfuse tracing across the full multi-agent pipeline |

---

## Architecture

```
User (Browser)
     │
     ▼
React Frontend (Vite + Tailwind + Plotly.js)
     │  POST /query  { query, refined_query? }
     ▼
FastAPI Server (main.py)
     │
     ▼
┌─────────────────────────────────────┐
│          Orchestrator               │
│  ┌──────────────────────────────┐  │
│  │  1. Intent Router            │  │
│  │  2. Ambiguity Checker        │  │
│  │  3. SQL Generator            │  │
│  │  4. SQL Guardrails           │  │
│  │  5. Database Executor        │  │
│  │  6. Result Interpreter       │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
     │
     ▼
Supabase PostgreSQL (hospital data)
     │
     ▼
Response: { status, sql_query, visualization, tokens, cost, latency }
```

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| API Server | FastAPI + Uvicorn |
| LLM Gateway | OpenRouter (gpt-4o-mini default) |
| Database | Supabase PostgreSQL via SQLAlchemy |
| Observability | Langfuse |
| Visualisation | Plotly Express |
| Config | PyYAML + python-dotenv |

### Frontend
| Layer | Technology |
|---|---|
| Framework | React 18 + Vite |
| Styling | Tailwind CSS 3 |
| Charts | Plotly.js + react-plotly.js |
| Routing | React Router v6 |
| Animations | Framer Motion |
| Icons | Lucide React |
| HTTP | Axios |

---

## Project Structure

```
mini-project-04/
├── main.py                        # FastAPI server entry point
├── requirements.txt               # Python dependencies
├── config/
│   ├── models.yaml                # LLM model IDs per provider/tier
│   ├── params.yaml                # Runtime config (provider, temperature, etc.)
│   └── schema.yaml                # Database schema for SQL generation
├── src/
│   ├── agents/
│   │   ├── orchestrator.py        # Multi-agent pipeline controller
│   │   ├── intent_router.py       # SQL vs GENERAL classification
│   │   ├── sql_generator.py       # NL → PostgreSQL translation
│   │   ├── result_interpreter.py  # Visualisation selection + AI insights
│   │   └── prompts/               # LLM system prompts
│   └── infrastructure/
│       ├── config.py              # Config loader + token counter
│       ├── llm/llm_providers.py   # LLM provider abstraction
│       ├── db/                    # SQLAlchemy + Supabase clients
│       └── guardrails/            # SQL safety validation
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── main.jsx               # React entry point
│       ├── App.jsx                # Router + layout
│       ├── pages/
│       │   ├── Home.jsx           # Landing page
│       │   ├── Dashboard.jsx      # Charts + chat interface
│       │   ├── Settings.jsx       # Usage analytics
│       │   └── Help.jsx           # Docs + architecture
│       ├── components/
│       │   ├── layout/Navbar.jsx
│       │   ├── common/            # PlotlyChart, LoadingSpinner, DarkModeToggle
│       │   └── dashboard/         # ChatInterface, PrebuiltCharts, ResultDisplay, etc.
│       ├── context/               # ThemeContext, QueryContext
│       └── utils/                 # api.js, exportUtils.js
└── diagrams/                      # ER and flow diagrams
```

---

## Getting Started

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **npm** or **pnpm**
- A **Supabase** project with the hospital schema (see `sql/medicore_data.sql`)
- An **OpenRouter** API key (or OpenAI key)

---

### Backend Setup

**1. Clone the repository**
```bash
git clone https://github.com/hemalmewan/medicore.git
cd medicore
```

**2. Create and activate a virtual environment**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

**3. Install Python dependencies**
```bash
pip install -r requirements.txt
pip install fastapi uvicorn
```

**4. Configure environment variables**

Copy `.env.sample` to `.env` and fill in your credentials:
```bash
cp .env.sample .env
```

```dotenv
# .env
OPENROUTER_API_KEY=sk-or-v1-...
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_KEY=...
SUPABASE_DB_URL=postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres
LANGFUSE_SECRET_KEY=sk-lf-...      # optional — for observability
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

**5. Start the FastAPI server**
```bash
python main.py
# or
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Swagger docs: `http://localhost:8000/docs`

---

### Frontend Setup

**1. Navigate to the frontend directory**
```bash
cd frontend
```

**2. Install dependencies**
```bash
npm install
```

**3. Configure the API URL (optional)**

The default points to `http://localhost:8000`. To change it, edit `frontend/.env`:
```dotenv
VITE_API_URL=http://localhost:8000
```

**4. Start the development server**
```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

**5. Build for production**
```bash
npm run build
```

---

## API Reference

### `GET /health`
Health check.

**Response:**
```json
{ "status": "ok", "service": "Medicore NL2SQL API" }
```

---

### `POST /query`
Execute the NL2SQL pipeline for a user query.

**Request body:**
```json
{
  "query": "Show monthly revenue trends for 2024",
  "refined_query": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | ✅ | Natural language question from the user |
| `refined_query` | string | ❌ | Clarified query after ambiguity resolution |

**Response (success):**
```json
{
  "status": "success",
  "message": "SQL query generated successfully",
  "sql_query": "SELECT DATE_TRUNC('month', ...) ...",
  "visualization": {
    "type": "chart",
    "chart_type": "line",
    "figure": { "data": [...], "layout": {...} },
    "insights": "Revenue increased by 18% between January and December...",
    "total_tokens": 84,
    "token_cost": 0.0000126
  },
  "total_tokens": 312,
  "token_cost": 0.0000468,
  "latency_ms": 1842
}
```

**Response (ambiguous):**
```json
{
  "status": "ambiguous",
  "message": "Query needs clarification. Please provide more detail.",
  "latency_ms": 540,
  "total_tokens": 96,
  "token_cost": 0.0000144
}
```

**Response statuses:**
| Status | Meaning |
|---|---|
| `success` | SQL executed and results visualised |
| `ambiguous` | Query too vague — frontend shows refinement modal |
| `ignored` | Input is not a data query (GENERAL intent) |
| `error` | Unexpected pipeline failure |

---

## Agent Pipeline

The `Orchestrator` chains 6 agents in sequence:

```
1. Intent Router       → classify "SQL" vs "GENERAL"
2. Ambiguity Checker   → flag unclear queries
3. SQL Generator       → NL → PostgreSQL (schema-aware)
4. SQL Guardrails      → safety validation (SELECT-only)
5. Database Executor   → Supabase query execution
6. Result Interpreter  → chart/table/text selection + AI insights
```

If `refined_query` is provided in the request, steps 1–2 are skipped and the pipeline starts directly at step 3.

---

## Database Schema

The Supabase database contains **12 tables** representing a hospital management system:

| Table | Description |
|---|---|
| `patients` | Patient demographics and contact info |
| `doctors` | Doctor profiles, specialties, departments |
| `specialties` | Medical specialty definitions |
| `departments` | Hospital department list |
| `admissions` | Inpatient admission records |
| `appointments` | Outpatient appointment bookings |
| `diagnoses` | Diagnosis records linked to admissions |
| `lab_orders` | Laboratory test orders |
| `prescriptions` | Medication prescriptions |
| `billing_invoices` | Financial billing records |
| `payments` | Payment transactions |
| `staff` | Non-doctor hospital staff |

The full schema with sample data is in `sql/medicore_data.sql`.

---

## Configuration

### LLM Provider (`config/params.yaml`)
```yaml
provider:
  default: "openrouter"   # openrouter | openai | anthropic | google | groq | deepseek
  tier: "general"         # general | strong | reason
llm:
  temperature: 0.2
  max_tokens: 3000
observability:
  enabled: true           # set false to disable Langfuse
```

### Model Tiers (`config/models.yaml`)
| Tier | OpenRouter | Use case |
|---|---|---|
| `general` | `openai/gpt-4o-mini` | Default — fast and cost-efficient |
| `strong` | `openai/gpt-4o` | Complex multi-table queries |
| `reason` | `openai/o3-mini` | Advanced reasoning tasks |

---

## Screenshots

| Page | Description |
|---|---|
| **Home** | Hero section, product overview, features, developer bio |
| **Dashboard** | 4 pre-built analytics charts + AI chat interface |
| **Settings** | Token usage, cost, latency metrics + query history |
| **Help** | Architecture diagram, how-to guide, agent descriptions |

---

## Developer

**Hemal Mewantha**  
Final Year Data Science Undergraduate — University of Colombo  
📧 mewanmuna2000@gmail.com  
🔗 [GitHub](https://github.com/hemalmewan) · [LinkedIn](https://www.linkedin.com/in/hemal-mewantha)

---

> Built as part of the **AI Engineering Bootcamp — Mini Project 04**  
> Powered by OpenRouter · Supabase · Langfuse · React · FastAPI
