# People Search & Reachout

Paste a job description, search for matching candidates across **People Data
Labs, Apollo.io, Proxycurl, or Coresignal**, then launch automated AI voice
outreach calls via **Hunar.ai**. Call conversations, structured Q&A results,
and recordings are saved to Postgres and viewable in a dashboard at any time.

## Tech stack

- **Frontend:** React + TypeScript (Vite)
- **Backend:** Python (FastAPI)
- **Database:** PostgreSQL
- **Auth:** Simple username/password (bcrypt-hashed passwords, JWT sessions)
- **Voice agent:** [Hunar.ai](https://api.voice.hunar.ai/docs/external/)
- **People search:** People Data Labs (PDL), Apollo.io, Proxycurl, Coresignal

## How it works

1. **Paste a job description.** The backend runs a lightweight, rule-based
   parser to extract keywords/skills, locations, and seniority — no external
   LLM call needed. You can edit any of the extracted criteria before
   searching.
2. **Search for candidates.** Pick a provider (PDL / Apollo / Proxycurl /
   Coresignal) and run a search. Results are normalized into a common
   candidate shape and saved to Postgres.
3. **Add phone numbers** for the candidates you want to call (E.164 format,
   e.g. `+15551234567`), then select them and click **"Call via Hunar.ai"**.
   This creates a real outbound call through your configured Hunar voice
   agent, passing the job title/company/location as `custom_data` variables.
   The call icon is only enabled once a candidate has a phone number on file.
   Next to it, a schedule icon lets you place the call within a calling
   window instead (pick days + a time range + timezone); see "Scheduling
   calls" below. Once a call is in flight or waiting to start, a cancel icon
   appears so you can stop it from this app's side.
4. **Hunar calls the candidate**, has a natural conversation, and (once the
   call ends) sends webhook events back to this app: call status, recording
   URL, and a structured **result** object (the Q&A / qualification data your
   Hunar agent's `result_schema` is configured to extract).
5. **View it all in the dashboard** — every call's status, duration,
   recording, and structured answers are saved and can be revisited anytime,
   filtered by status, grouped by job description.

### Scheduling calls

Next to each candidate's immediate-call icon is a schedule icon
(🗓️) that opens a **Schedule a call** screen: pick an agent, at least 3
calling days, a start/end time (≥3 hours apart), and a timezone. Saving
creates a `CallSchedule` row that stays **PENDING** — nothing is sent to
Hunar yet.

A background loop (in `app/main.py`) checks every 60 seconds for pending
schedules whose window has opened and dispatches them to Hunar automatically,
passing the window along as `guardrails` + `timezone` on the call. Because
this app is the only thing that ever turns a pending schedule into a real
call, a schedule can be **updated or deleted at any time before its window
opens** — that's a real, guaranteed cancellation, unlike cancelling a call
that's already been placed (see below).

The **Schedules** page (`/schedules`) lists everything: pending schedules
(with Update / Call now / Delete), and dispatched/cancelled/failed ones for
reference. It also lists your past conversations with a **"Schedule
again"** link so you can quickly set up a follow-up call for a candidate
you've already called.

### Cancelling a call

Hunar's external API does not expose an endpoint to abort a call once it's
been handed to the telephony provider — there's no cancel/delete on
`/calls/{id}/`. The **Cancel** action available on the candidate row, the
Conversations page, and the call detail page is therefore a best-effort,
local action: it marks the call `CANCELLED` in this app (so it stops being
tracked, retried, or shown as active) and is clearly noted as such. If the
call hadn't started ringing yet, it very likely never will; if it had
already connected, Hunar may still run it to completion on their end. The
one case where cancelling is *guaranteed* to prevent the call from ever
happening is deleting a still-**PENDING** schedule, since this app hasn't
sent anything to Hunar for it yet.


### Demo mode (no API keys required)

Every people-search provider adapter falls back to realistic **mock
candidate data** if its API key isn't configured, so you can exercise the
entire UI (search → select → "call") without signing up for anything. The
same applies to Hunar: if `HUNAR_API_KEY` isn't set, outreach requests are
recorded in the dashboard but not actually dispatched, so you can see the
whole flow before wiring up real credentials.

## Project structure

```
backend/
  app/
    main.py                 FastAPI app, CORS, startup (creates tables + default admin)
    config.py                Environment-based settings
    database.py               SQLAlchemy engine/session
    models.py                  User, JobDescription, Candidate, OutreachCall, CallEvent
    schemas.py                  Pydantic request/response models
    security.py                  Password hashing + JWT
    deps.py                       get_current_user dependency
    routers/
      auth.py            /api/auth/register, /login, /me
      jobs.py             /api/jobs           JD CRUD + criteria editing
      search.py            /api/jobs/{id}/search, /candidates   provider search + candidate mgmt
      agents.py             /api/agents         builds/updates agents directly via the Hunar API
      outreach.py           /api/jobs/{id}/outreach, /calls      launch Hunar calls
      dashboard.py           /api/dashboard/*                     cross-job call views, sync, summary
    providers/           PDL / Apollo / Proxycurl / Coresignal adapters (common interface + mock fallback)
    services/
      jd_parser.py       rule-based JD -> search-criteria extraction
      hunar_client.py     Hunar Voice Agents API client (agents, calls, numbers)

frontend/
  src/
    pages/            Login, JobDescriptions, JobDetail, Agents, CallsDashboard, CallDetail, Dashboard
    api/               axios client + typed endpoint wrappers
    context/            AuthContext (JWT stored in localStorage)
    components/          Layout/sidebar, StatusBadge, ResultPreview, ProtectedRoute
```

## Running locally with Docker (recommended)

1. Copy the env templates and fill in whatever API keys you have (all are
   optional — leave blank to run any given provider in demo mode):

   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

2. At minimum, set a real `JWT_SECRET` in `backend/.env`. To actually place
   calls, also set `HUNAR_API_KEY` (get it from your Hunar account) — you
   build the voice agent itself from inside the app, no separate agent-id
   env var needed (see below).

3. Start everything:

   ```bash
   docker compose up --build
   ```

4. Open the app at **http://localhost:5173**. Sign in with the default admin
   account (`admin` / `changeme123` unless you changed
   `DEFAULT_ADMIN_USERNAME` / `DEFAULT_ADMIN_PASSWORD`), or register a new
   user from the login screen.

The backend is at **http://localhost:8000** (interactive API docs at
`/docs`), Postgres at `localhost:5432`.

## Running without Docker

**Backend**

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL to point at your local Postgres
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Setting up Hunar.ai

1. Get your `X-API-Key` from Hunar and set it as `HUNAR_API_KEY` in
   `backend/.env`.
2. In the app, go to **Agents → "+ Build a new agent"**. Fill in:
   - **Basics** — name, language, voice persona, and an optional display
     name for the persona.
   - **Conversation** — the objective, the agent's system prompt, its
     opening line, and optional silence/closing lines.
   - **Questions to capture** — add one row per thing you want the agent to
     find out (e.g. "Are they open to new roles?" → field name
     `open_to_roles` → Yes/No). These become the Hunar `result_schema` /
     `result_prompt` automatically — there's no JSON to write by hand.
3. Click **Create agent**. The backend calls Hunar's `POST /agents/` for you
   and stores the id Hunar returns — you never type an agent id in
   yourself. The agent card shows its live status (`DRAFT`/`ACTIVE`) and
   provider id/code once created.
4. Whatever field names you used in the question builder are exactly what
   will show up as the call's "Response" on the dashboard and as
   "Conversation results" on each call's detail page.
5. Editing an agent later (name, prompt, questions, etc.) pushes the same
   fields to Hunar's `PUT /agents/{id}/` so the two stay in sync.

There's no inbound webhook receiver in this app — call status, recordings,
and results are pulled on demand. Use the **"Refresh status"** button on the
Conversations page to poll `GET /calls/{id}` for every call that hasn't
reached a terminal status yet.

## Setting up people-search providers

Set whichever of these you have access to; unset ones run in demo mode:

| Provider | Env var | Docs |
|---|---|---|
| People Data Labs | `PDL_API_KEY` | https://docs.peopledatalabs.com/docs/person-search-api |
| Apollo.io | `APOLLO_API_KEY` | https://docs.apollo.io/reference/people-search |
| Proxycurl | `PROXYCURL_API_KEY` | https://nubela.co/proxycurl/docs#people-api-person-search-api |
| Coresignal | `CORESIGNAL_API_KEY` | https://docs.coresignal.com/ |

**Note on phone numbers:** none of these providers reliably return direct
mobile numbers (Apollo can via its paid phone-enrichment add-on; the others
generally don't). Add/edit a candidate's phone number directly in the UI
(click the phone cell in the candidates table) before launching outreach —
Hunar requires a valid E.164 number to place a call.

## Security notes for production use

- Change `JWT_SECRET`, `DEFAULT_ADMIN_PASSWORD`, and the Postgres credentials
  before deploying anywhere public.
- Put the backend behind HTTPS — JWTs and your `HUNAR_API_KEY` should never
  travel over plain HTTP.

## Schema note for existing installs

This version adds several new columns to the `agents` table (language,
voice persona, prompt fields, result schema, etc.) to support building
agents from inside the app. Since the app uses SQLAlchemy's
`Base.metadata.create_all` (no Alembic migrations), it will **not**
retroactively alter an existing `agents` table. If you're upgrading a
database that already has the old schema, drop the `agents` table (or the
whole dev database) once before starting the backend so it gets recreated
with the new columns.


