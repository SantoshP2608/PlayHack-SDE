# SlotGrab shared AI context

This is the source of truth for people and AI agents working on this repository. Read it before making a change and update it in the **same change set** whenever project behaviour, architecture, dependencies, test coverage, configuration, or known limitations change.

## Current product

SlotGrab is a web application for IIT Guwahati students to discover sports facilities, choose a one-hour slot, reserve a whole court, and join a waitlist when a slot is unavailable.

The core competition rule is: **one valid booking may exist for one facility/court and one time slot.** The eventual backend must prove this under concurrent requests.

## Current implementation

- **Runtime:** Next.js 16, React 19, JavaScript, Tailwind CSS 4.
- **Entry route:** `app/page.js` renders the `SlotGrab` component.
- **Main UI:** `components/SlotGrab.js` is a client component that handles exploration, booking feedback, waitlist interaction, cancellation, the My bookings view, and demo outcomes.
- **Visual asset:** `components/CourtIllustration.js` draws the court illustration used in the hero area.
- **Frontend state:** `lib/demo-bookings.mjs` holds sample sports, dates, slots, status rules, and the in-memory reducer.
- **Styling:** `app/globals.css` defines the approved green Campus Club visual system and responsive behaviour.
- **Tests:** `tests/demo-bookings.test.mjs` tests reducer behaviour only.
- **Backend foundation (Milestone 1):** `backend/app/models.py` defines the five approved V1 SQLAlchemy models. FastAPI exposes `/health` and `/docs`; psycopg 3 connects to PostgreSQL without Supabase. Sync request-scoped sessions and pooled connections are provided in `database.py`.
- **Catalogue (Phase 2):** `backend/app/routes/catalogue.py` exposes GET `/api/sports`, `/api/facilities?sport_id=...`, and `/api/slots?facility_id=...&date=YYYY-MM-DD`. Public response contracts are in `schemas.py`. Active facilities only in lists; direct slot lookup marks inactive facilities/past or started slots UNAVAILABLE, otherwise confirmed bookings BOOKED and remaining slots AVAILABLE. Availability is calculated in SQL using PostgreSQL's current statement time in Asia/Kolkata; no stored status or 12-hour release rule. Responses are uncached snapshots, not reservations.
- **Booking (Phase 3):** `backend/app/routes/bookings.py` exposes POST `/api/bookings` and GET `/api/demo/users`. Booking is enabled only with `SLOTGRAB_DEMO_MODE=1` and a local peer, using a synthetic ID header; this is not real authentication. The route locks slot/facility rows, checks bookability, inserts a confirmed booking in one transaction, and handles duplicate request keys. PostgreSQL's partial unique index is the final one-confirmed-booking guarantee. See `backend/README.md` for request/response contracts.
- **Concurrency proof (Phase 4):** `python -m app.race_demo` targets the live loopback API, synchronizes 50 distinct synthetic users against one free future slot, and independently verifies the confirmed-row count in PostgreSQL. It passes only for one `201`, 49 clean booking conflicts, one database row and zero overselling; it never resets shared data.
- **Backend setup:** see `backend/README.md`. Explicit create-database, table initialization and repeatable seed commands; an isolated Windows development cluster can run on localhost port 55432. Credentials and cluster files are ignored.
- **Verified local state (2026-09-23):** PostgreSQL 18 database `slotgrab` on 127.0.0.1:55432; 3 sports, 11 facilities, 110 slots for 25-26 September, a separate 2099 demo seed, and 50 synthetic users. Live Phase 3/4 checks created confirmed bookings for slot 281 and slot 1; demo bookings are intentionally retained. FastAPI was running on 127.0.0.1:8000 with health/docs checked over HTTP. Process availability must be rechecked in future sessions.
- **Dependency reproducibility:** direct ranges in `backend/requirements.txt`; tested resolved versions in `backend/requirements.lock.txt`. Python 3.14 was used locally. Install the lock file for the same environment.

## Confirmed behaviours

- Users can browse Badminton, Tennis, and Basketball sample courts for 25 and 26 September 2026.
- A 60-minute court slot can be booked, cancelled, or waitlisted in the frontend demo.
- Demo controls can simulate a successful booking, a booking conflict, or a failed request.
- The local reducer prevents repeated clicks from producing duplicate local booking entries.

## Boundaries and non-claims

- The frontend remains an **in-memory prototype**. Its state disappears on refresh; backend integration is pending.
- Backend foundation, read-only catalogue and local demo booking are implemented. There is no production authentication, frontend integration, booking cancellation API, waitlist promotion, notifications, institutional SSO or deployed backend.
- V1 backend excludes waitlist and closures. Frontend waitlist remains simulation only. The local booking header is an explicit demo-only exception: replace it with authenticated identity before deployment. Email domain checks alone do not verify identity.
- Database rules use whole-hour same-day IST slots and one CONFIRMED booking per slot; cancelled rows retain history. Booking API now implements UUID request validation and retry replay for a successful active booking; reuse after cancellation or for another slot returns 409.
- Seed provenance is documented in `backend/README.md`: PDF sample courts/hours; caller-selected dates; opt-in synthetic users. Backend data differs from existing frontend samples until catalogue integration.
- The frontend reducer is not a concurrency guarantee. The backend database test now proves 50 simultaneous distinct users produce one confirmed booking; the frontend remains unconnected.
- Sample facilities, times, blocked slots, and queue positions are demo data, not confirmed IITG operational data.

## Required workflow for every agent and change

1. Before editing, inspect `git status`, read this file plus `AGENTS.md`, then run `git fetch origin` and inspect the incoming commit diff. If the tree is clean, fast-forward to the remote version before work; if it is not clean, preserve the local work and resolve the divergence before editing overlapping files.
2. Review the diff before work. If another contributor changed product behaviour, dependencies, architecture, tests, configuration, or a limitation, update the relevant section here before relying on it.
3. Make the code change and update this file in the same working change set. Add a dated entry to the changelog for every meaningful project change; do not erase earlier entries.
4. Run the relevant verification. At minimum run `npm.cmd test` for JavaScript state/UI changes; also run `npm.cmd run build` for application, dependency, configuration, or styling changes when dependencies are installed.
5. Before handing work over, inspect `git diff` and verify that this file accurately describes the resulting state. Never describe a simulated frontend action as a database-backed guarantee.

## Commands

```powershell
npm.cmd install
npm.cmd test
npm.cmd run build
npm.cmd run dev
```

Use `npm.cmd` on Windows because PowerShell may block `npm.ps1`.

## Change log

### 2026-09-23 - Phase 4 repeatable live concurrency proof

- Added a loopback-only race demonstration command that automatically selects an active free future slot, obtains synthetic identities from the live API, and releases up to 50 HTTP requests together.
- Added strict result evaluation and a direct post-race PostgreSQL count. PASS requires exactly one HTTP winner, every other response to be `409 SLOT_ALREADY_BOOKED`, exactly one confirmed database row, and zero overselling. Failures and transport errors are grouped for diagnosis, and the command returns a nonzero exit code.
- The command does not delete/reset data; each successful demonstration consumes one slot. Added README operation and expected-output instructions plus focused tests that prevent false PASS results and external race targets.
- Verification: 45 PostgreSQL-backed tests passed with one upstream Starlette/httpx deprecation warning; `git diff --check` passed. The live command raced 50 requests against slot 1 and reported one `201`, 49 clean conflicts, one confirmed database row, zero overselling and PASS in 3.38 seconds.

### 2026-09-23 - Phase 3 local booking and synchronized baseline

- Committed and pushed Phase 1/2 to `origin/main` as `ec5559a`; excluded unrelated local `package-lock.json` edits and ignored secrets/database files.
- Added opt-in localhost demo identity listing and POST booking API. The transaction blocks on `FOR UPDATE`, checks identity, facility activity, slot start time and existing booking, then inserts and commits. Existing successful retries return the same booking; different slot/cancelled reuse returns 409. A database unique violation is recovered to a controlled response.
- Added real PostgreSQL integration tests for booking responses, identity guard, validation, cancellation history, catalogue status, 50 concurrent users and concurrent same-key retries. Final full run: 42 passed with one upstream Starlette/httpx deprecation warning. `git diff --check` passed.
- Added Swagger manual test instructions and exact response/error contracts to backend README. Live local HTTP test with a 2099 sample slot returned 201 for the winner, 200 for the identical retry, 409 SLOT_ALREADY_BOOKED for a second user and BOOKED on catalogue reread. This added one demo booking on slot 281; earlier 2026 seed data remains unchanged. Git history is the source for Phase 3 publish status.

### 2026-09-23 - Phase 2 catalogue API verified

- Fetched origin; no incoming commits. Preserved all pre-existing work and package-lock.json changes.
- Added catalogue router and public response schemas; sport/facility IDs must be positive PostgreSQL bigint values, date is required and validated. Missing parents return 404, existing empty results return [], invalid queries return 422. Database failures return a generic 503 without SQL/connection details.
- Slot availability uses a single SQL query with confirmed-booking EXISTS and facility/time checks; cancelled history does not block availability. Catalogue success responses have Cache-Control: no-store.
- Moved reusable database fixtures into tests/conftest.py. Added PostgreSQL integration coverage for catalogue reads, availability transitions, inactive/past slots, input errors, outage behaviour and OpenAPI. No new dependencies or schema migration.
- Verification: 35 PostgreSQL-backed tests passed (16 foundation + 19 catalogue cases), with the existing upstream Starlette/httpx deprecation warning. Next.js production build and git diff whitespace check passed. Restarted local Uvicorn and verified live sports (3), Badminton facilities (10), five available slots for a returned facility on 2026-09-25, and Swagger HTTP 200.
- Updated backend README with response contracts, status precedence, error behaviour and manual Swagger checklist. No migrations, commits or pushes. Frontend integration and booking writes remain later milestones.

### 2026-09-23 - Milestone 1 backend foundation verified

- Fetched origin; main remains at `4f6d021`, with no incoming commits. Preserved existing AGENTS.md/context changes and unrelated package-lock.json changes.
- Added SQLAlchemy User, Sport, Facility, Slot and Booking models, including PostgreSQL enum, foreign keys, checks and partial unique booking index. Added a nonblank idempotency-key check to the approved schema.
- Added FastAPI health/Swagger, pooled psycopg connections, explicit initialization and atomic insert-only seed CLI. Switched the earlier asyncpg proposal to synchronous SQLAlchemy/psycopg per the user's request.
- Added private local PostgreSQL startup helper with generated SCRAM password, backend dependencies, env example, setup/provenance documentation, and integration tests. No frontend integration or booking API is included.
- Initialized the isolated local database and ran initialization/seeding twice; verified counts remain 3 sports, 11 facilities, 110 slots, 50 users and 0 bookings.
- Verification: 16 PostgreSQL integration tests passed (including repeat initialization, duplicate-slot rejection and restricted parent deletion); one upstream Starlette/httpx deprecation warning. `pip check` passed. Existing frontend tests: 3 passed; Next.js production build passed. Live `/health` returned 200/connected and `/docs` returned 200. `git diff --check` passed and local secrets/data/venv were confirmed ignored.
- These checks prove the foundation and database constraints, not the future 50-request API race demonstration. Application startup does not create/seed tables. No commits or pushes were made.

### 2026-09-23 - Shared AI context established

- Cloned the repository and documented the current frontend-only SlotGrab prototype.
- Confirmed the existing reducer test suite passes: 3 tests passed.
- Added a mandatory synchronization, documentation, and verification workflow for future contributors and AI agents.
