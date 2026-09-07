# Reachout

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


### Demo mode (no API keys required)

Every people-search provider adapter falls back to realistic **mock
candidate data** if its API key isn't configured, so you can exercise the
entire UI (search → select → "call") without signing up for anything. The
same applies to Hunar: if `HUNAR_API_KEY` isn't set, outreach requests are
recorded in the dashboard but not actually dispatched, so you can see the
whole flow before wiring up real credentials.



