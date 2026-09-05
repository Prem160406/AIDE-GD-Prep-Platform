# AIDE — Automated Intelligent Discussion Engine

> AI-powered Group Discussion topic generator and placement prep platform for campus recruitment.

---

## Overview

**AIDE** is a full-stack, resume-grade web platform that automatically ingests breaking news RSS feeds, extracts article context, evaluates GD topic suitability using an 8-dimension AI scoring rubric (Gemini LLM), applies hard-filter quality vetos, and persists high-scoring discussion cards to Supabase.

Students, Placement Officers (TPOs), Recruiting Companies, and Master Administrators interact with role-specific dashboards governed by server-side Row Level Security (RLS) policies.

---

## Architecture

```
                       ┌─────────────────────────────────────┐
                       │          RSS News Feeds             │
                       └──────────────────┬──────────────────┘
                                          │
                                          ▼
                       ┌─────────────────────────────────────┐
                       │         Python AI Pipeline          │
                       │   (collect -> fetch -> LLM score)   │
                       └──────────────────┬──────────────────┘
                                          │
                                          ▼  Direct Service Role Write
                       ┌─────────────────────────────────────┐
                       │         Supabase PostgreSQL         │
                       │  (topics, profiles, system_status,  │
                       │   pipeline_jobs, pipeline_runs)     │
                       └──────────────────┬──────────────────┘
                                          │
                        Direct Browser Read (RLS Enforced)
                                          │
                       ┌──────────────────┴──────────────────┐
                       │           React Frontend            │
                       │ (Student / TPO / Company / Admin)   │
                       └─────────────────────────────────────┘
```

- **React Frontend**: Single Page Application built with React 19 and `@supabase/supabase-js`. Connects directly to Supabase with RLS role-enforced queries.
- **AI Scoring Pipeline**: Asynchronous Python pipeline (`collector.py`, `fetcher.py`, `prompt.py`, `llm_client.py`, `scorer.py`, `pipeline.py`, `output.py`).
- **Database Layer**: Supabase PostgreSQL with custom RLS policies, atomic auth triggers, job queue management, and maintenance lockout controls.

---

## Role-Based Access & Security Matrix

| Role | Topic Permissions | Features & Dashboards |
|---|---|---|
| **Student** | Read `published` topics only | Practice tracking (`practiced_topics`), search, card views |
| **Company** | Read `published` topics only | Drive shortlisting (`shortlisted_topics`), analytical tags |
| **TPO** | Read `published` & `archived` topics | Analytical tags, CSV export for faculty/placement reports |
| **Master Admin** | Read/Write ALL statuses (`published`, `archived`, `draft`) | Maintenance toggle, manual job queue trigger, run telemetry logs |

*All roles are verified server-side via the `public.profiles` table and atomic database triggers—never via client-editable `user_metadata`.*

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js v18+
- A Supabase Project
- A Gemini API Key

### 1. Database Setup
Run the SQL migration script (found in database schema documentation) in your **Supabase Dashboard → SQL Editor** to create `topics`, `profiles`, `system_status`, `pipeline_jobs`, `pipeline_runs`, `practiced_topics`, and `shortlisted_topics` tables and RLS policies.

### 2. Environment Configuration
Copy `.env.example` to `.env` in the root directory and `frontend/.env` in the frontend directory:

```bash
# Root .env (Python Pipeline)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-service-role-key
GEMINI_API_KEY=your-gemini-api-key

# frontend/.env (React Client)
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-supabase-anon-public-key
```

### 3. Backend Pipeline Installation

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Frontend Installation & Running

```bash
cd frontend
npm install
npm start
```

---

## Running the Pipeline

### Option A: One-Shot CLI Execution
Run the pipeline directly from the command line:
```bash
python __main__.py --feed-limit 10
```

### Option B: Background Worker Mode (Job Queue Listener)
Run the pipeline in continuous background worker mode to process manual triggers requested by the Master Admin from the UI:
```bash
python __main__.py --listen
```

### Option C: Automated Scheduled Cron
Add a crontab entry or scheduled task to run `python __main__.py` automatically on a periodic schedule (e.g. weekly).

---

## Testing

Run unit tests using `pytest`:
```bash
pytest test_scorer.py
```