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
- **Backend setup:** see `backend/README.md`. Explicit create-database, table initialization and repeatable seed commands; an isolated Windows development cluster can run on localhost port 55432. Credentials and cluster files are ignored.
- **Verified local state (2026-09-23):** PostgreSQL 18 database `slotgrab` on 127.0.0.1:55432; 3 sports, 11 facilities, 110 slots for 25-26 September and 50 synthetic users, zero bookings. FastAPI was started on 127.0.0.1:8000 and its health/docs checked over HTTP. Process availability must be rechecked in future sessions.
- **Dependency reproducibility:** direct ranges in `backend/requirements.txt`; tested resolved versions in `backend/requirements.lock.txt`. Python 3.14 was used locally. Install the lock file for the same environment.

## Confirmed behaviours

- Users can browse Badminton, Tennis, and Basketball sample courts for 25 and 26 September 2026.
- A 60-minute court slot can be booked, cancelled, or waitlisted in the frontend demo.
- Demo controls can simulate a successful booking, a booking conflict, or a failed request.
- The local reducer prevents repeated clicks from producing duplicate local booking entries.

## Boundaries and non-claims

- The frontend remains an **in-memory prototype**. Its state disappears on refresh; backend integration is pending.
- Backend foundation and read-only catalogue are implemented. There are no booking endpoints, authentication, live multi-user UI, waitlist promotion, notifications, institutional SSO or deployed backend.
- V1 backend excludes waitlist and closures. Frontend waitlist remains simulation only. Booking endpoints must take identity from authentication, never trust a supplied user ID. Email domain checks alone do not verify identity.
- Database rules use whole-hour same-day IST slots and one CONFIRMED booking per slot; cancelled rows retain history. The successful-request idempotency key constraint does not by itself implement API retries or payload validation.
- Seed provenance is documented in `backend/README.md`: PDF sample courts/hours; caller-selected dates; opt-in synthetic users. Backend data differs from existing frontend samples until catalogue integration.
- The reducer is not a concurrency guarantee. A future database-backed booking endpoint must enforce one booking per court/time slot atomically and support idempotent retries.
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
