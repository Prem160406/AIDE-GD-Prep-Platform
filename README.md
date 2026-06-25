# AIDE — Automated Intelligent Discussion Engine

> AI-powered Group Discussion topic generator for campus placement preparation

---

## What is AIDE

AIDE is a full-stack web application that automatically scrapes breaking news, scores articles for Group Discussion suitability using an AI pipeline, and pushes the best topics to a database. Students, TPOs, and companies can then browse these topics on a role-specific dashboard.

The system has three independent parts:

- **AI Pipeline** — scrapes news, scores articles, writes to Supabase
- **FastAPI Backend** — reads from Supabase, exposes REST API, triggers the pipeline
- **React Frontend** — login, role-based dashboards, topic cards

---

## Architecture

```
AI Pipeline (__main__.py)
      |
      v  writes directly
   Supabase (topics table)
      ^
      |  reads
FastAPI (back_main.py)  <---->  React Frontend (frontend/src/)
   port 8000                        port 3000
```

The pipeline never goes through FastAPI — it writes directly to Supabase via REST. FastAPI only reads from Supabase and can trigger the pipeline as a subprocess.

---

## Folder Structure

```
AIDE-GD-Prep-Platform/
├── back_main.py              # FastAPI backend
├── __main__.py               # Pipeline entry point
├── config.py                 # Pipeline configuration
├── models.py                 # Data models
├── utils.py                  # Utility functions
├── collector.py              # RSS feed collector
├── fetcher.py                # Article fetcher
├── prompt.py                 # Prompt builder
├── llm_client.py             # LLM client
├── scorer.py                 # Scoring engine
├── pipeline.py               # Pipeline orchestrator
├── output.py                 # Supabase writer + file outputs
├── requirements.txt          # Python dependencies
├── .env                      # Backend secrets (never commit)
│
└── frontend/                 # React app
    ├── .env                  # Frontend secrets (never commit)
    ├── package.json
    └── src/
        ├── index.js
        ├── App.js            # Auth check + role routing
        ├── supabase.js       # Supabase client
        ├── features/
        │   ├── auth/
        │   │   └── AuthPage.jsx
        │   ├── student/
        │   │   └── StudentDashboard.jsx
        │   ├── tpo/
        │   │   └── TPODashboard.jsx
        │   └── company/
        │       └── CompanyDashboard.jsx
        └── services/
            └── api.js        # FastAPI calls
```

---

## Supabase Setup

Three tables are required in your Supabase project:

### topics (written by pipeline)

| Column | Type |
|---|---|
| id | bigint |
| title | text |
| summary | text |
| source_url | text |
| source_name | text |
| status | text |
| created_at | timestamptz |
| pipeline_version | text |
| weighted_score | numeric |
| decision | text |
| published | text |
| controversy | boolean |
| multiple_stakeholders | boolean |
| policy_relevance | boolean |
| ethical_dimension | boolean |
| factual_freshness | text |
| debate_balance | text |
| public_impact | text |
| topic_clarity | text |

### practiced_topics (student activity)

| Column | Type |
|---|---|
| id | bigint (auto) |
| user_id | uuid (references auth.users) |
| topic_id | bigint (references topics.id) |
| practiced_at | timestamptz (default now()) |

### shortlisted_topics (company activity)

| Column | Type |
|---|---|
| id | bigint (auto) |
| user_id | uuid (references auth.users) |
| topic_id | bigint (references topics.id) |
| shortlisted_at | timestamptz (default now()) |

Auth users are managed automatically by Supabase Auth. On signup, `full_name` and `role` are stored in `user_metadata`.

---

## Prerequisites

- Python 3.10+
- Node.js v18+ (LTS)
- A Supabase project (free tier works)
- A Gemini API key
- Git

---

## Installation & Setup

### Step 1 — Clone the repo

```bash
git clone https://github.com/Prem160406/AIDE-GD-Prep-Platform.git
cd AIDE-GD-Prep-Platform
```

### Step 2 — Create Python virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Step 3 — Create backend .env file

Create a file called `.env` in the root folder:

```
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_KEY=your-service-role-key
GEMINI_API_KEY=your-gemini-api-key
```

Get Supabase credentials from: **Supabase Dashboard → Settings → API**. Use the **service role key** for the backend.

### Step 4 — Install frontend dependencies

```bash
cd frontend
npm install
```

### Step 5 — Create frontend .env file

Create a file called `.env` inside the `frontend/` folder:

```
REACT_APP_SUPABASE_URL=https://yourproject.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-anon-public-key
REACT_APP_API_URL=http://localhost:8000
```

Use the **anon/public key** here. Found in **Supabase Dashboard → Settings → API → anon public**.

---

## Running the Project

You need two terminals open simultaneously.

**Terminal 1 — Backend**

```bash
# From the root folder
.venv\Scripts\activate       # Windows
source .venv/bin/activate     # Mac/Linux

uvicorn back_main:app --reload
```

Backend runs at `http://localhost:8000`

**Terminal 2 — Frontend**

```bash
cd frontend
npm start
```

Frontend runs at `http://localhost:3000`

---

## How It Works

### User flow

1. User opens `http://localhost:3000` and sees the login/signup page
2. On signup, user enters full name, email, password, and selects a role (Student / TPO / Company)
3. After login, `App.js` reads the role from Supabase `user_metadata` and routes to the correct dashboard
4. The dashboard fetches topics from FastAPI (`GET /api/topics`), which reads from Supabase
5. Cards are displayed with title, summary, source link, date, and score

### Generating new topics

1. A student clicks the **Generate New Topics** button
2. React calls `POST /api/run-pipeline` on the FastAPI backend
3. FastAPI runs `__main__.py` as a subprocess
4. The pipeline scrapes news, scores articles, and pushes qualifying rows directly to Supabase
5. The frontend automatically re-fetches topics after the pipeline completes

### Role-specific features

- **Student** — mark topics as "Practiced", stored in `practiced_topics` table
- **Company** — shortlist topics for campus drive GD rounds, stored in `shortlisted_topics` table
- **TPO** — export the full topic list as a CSV file

---

## API Reference (FastAPI)

### `GET /`
Health check. Returns `{"message": "AIDE Backend is connected to Supabase!"}`

### `GET /api/topics`
Returns all topics from Supabase ordered by `created_at` descending.

Response: `{"topics": [...], "total": N}`

### `GET /api/topics/{id}`
Returns a single topic by ID. Returns 404 if not found.

### `POST /api/run-pipeline`
Triggers `__main__.py` as a subprocess. Times out after 10 minutes.

---

## Environment Variables

### Root `.env` (backend)

```
SUPABASE_URL        # Your Supabase project URL
SUPABASE_KEY        # Service role key (keep secret, backend only)
GEMINI_API_KEY      # Your Gemini API key (keep secret)
```

### `frontend/.env` (React)

```
REACT_APP_SUPABASE_URL       # Same Supabase project URL
REACT_APP_SUPABASE_ANON_KEY  # Anon/public key (safe for frontend)
REACT_APP_API_URL            # http://localhost:8000 for local dev
```

Both `.env` files must be listed in `.gitignore` and never pushed to GitHub.

---

## .gitignore

```
# Python
.venv/
__pycache__/
*.pyc
.env
output/

# React
frontend/node_modules/
frontend/.env
frontend/build/

# OS
.DS_Store
Thumbs.db

# Debug
debug_run*.py
debug_run*.txt
```

---

## Common Issues

**Pipeline produces no topics** — Check your Gemini API key in `.env`. Also verify that `debate_balance`, `factual_freshness`, and `topic_clarity` hard filters are not too strict in `config.py`.

**Supabase insert fails** — Make sure you are using the **service role key** in the backend `.env`, not the anon key. The anon key is blocked by RLS for writes.

**Frontend shows no topics** — Make sure the anon key has a public SELECT policy on the `topics` table in Supabase.

**CORS error** — Backend only allows `localhost:3000`. If your frontend runs on a different port, update `allow_origins` in `back_main.py`.

---

## Project Info

- **Institution:** Vishwakarma Institute of Technology, Pune
- **Course:** ASEP2 — Group 6
- **Pipeline Version:** 1.2.0