# SlotGrab backend: foundation, catalogue and booking

Python 3.12+ and PostgreSQL 17+ are required. The verified local environment is Python 3.14 and PostgreSQL 18. No Supabase is used. Run the following commands from `backend/`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
```

The lock file records the tested dependency versions; `requirements.txt` lists the supported direct dependency ranges. The current Starlette test client emits a deprecation warning for httpx; the integration suite still passes.

## Local database on Windows

With PostgreSQL 18 installed at its default location:

```powershell
.\scripts\local-db.ps1
```

This initializes a separate project cluster under ignored `.local/postgres`, bound to `127.0.0.1:55432`. It generates a password, requires SCRAM authentication, and writes the connection URL to ignored `.env`. It does not change your existing Windows PostgreSQL service. Use `-PgBin` for a different installation. Keep `.local/` and `.env` private; the local `slotgrab` role is a development administrator, not a production application role.

Alternatively, configure your own PostgreSQL server: copy `.env.example` to `.env`, set its connection URL, and use an existing dedicated application database. `create_database` requires a role permitted to create databases; skip it if your database already exists.

```powershell
.\.venv\Scripts\python.exe -m app.create_database
.\.venv\Scripts\python.exe -m app.init_db
.\.venv\Scripts\python.exe -m app.seed --start-date 2026-09-25 --days 2 --test-users 50
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs or http://127.0.0.1:8000/health. A successful database probe returns HTTP 200 with `{"status":"ok","database":"connected"}`; an unavailable database returns HTTP 503 without credentials or internal error details. Health checks connectivity only, not schema readiness. Initialization and seeding are explicit commands, never automatic API startup side effects.

Stop the API using Ctrl+C. Stop only this project's database with `./scripts/local-db.ps1 -Action stop`.

## Schema and behaviour

`app/models.py` is the schema source: users, sports, facilities, slots, bookings. SQLAlchemy sessions and connection pooling use psycopg 3. Sync database operations run in sync FastAPI routes. No raw `schema.sql` or duplicate SQL schema is maintained.

- All slot dates and times mean Asia/Kolkata (IST). Audit timestamps use timezone-aware PostgreSQL timestamps. Slots are fixed, whole-hour, same-day sessions; 23:00-to-midnight slots are intentionally unsupported in this V1 schema.
- A partial unique index allows at most one CONFIRMED booking per slot while retaining cancelled history. A user/request-key unique constraint supports later successful-request retry handling. API-level idempotency replay, payload checks, transactions, identity verification and authorization remain to be implemented.
- The email-domain constraint is formatting validation, not proof that an account is verified. No login endpoint exists yet. Future booking routes must derive the user from authenticated identity, not trust a caller-supplied user ID.
- Availability will be derived from confirmed bookings and facility activity; no stored slot status exists. Future booking routes must reject inactive facilities and past slots. `is_active` is a catalogue switch, not a closure scheduling system.
- `init_db` creates missing objects and preserves existing data. It does not migrate existing columns or indexes. Introduce explicit migrations before changing a populated schema.

## Seed provenance and limits

Sources are the team's `PS.pdf` and `SlotGrab_DevMania.pdf`, supplied in the parent planning workspace. They are not runtime dependencies.

| Seed | Source and interpretation |
| --- | --- |
| Badminton, Tennis, Football | Official brief p. 2 facility examples; only the court subset has concrete locations in the deck |
| Badminton: Old SAC courts 1-6 and New SAC courts 1-4 | Deck p. 8 Badminton court map; examples, not verified campus inventory |
| Tennis: New SAC Court 1 | Deck p. 7 pinned-court example |
| Starts 16:00, 17:00, 18:00, 19:00, 20:00 IST | Deck p. 8 time bar, using the approved one-hour rule; deck pp. 7 and 10 explicitly show 18:00-19:00 |
| Dates 25-26 September 2026 | Explicit CLI demo dates aligned to the event; the deck says Today and does not assign these dates to its examples |
| 50 users (only with `--test-users 50`) | Synthetic numbered identities with dummy institute-domain emails, not PDF people or verified users; never send them email |

Two days produce 3 sports, 11 facilities and 110 slots. Football has no seeded facilities because the PDFs do not identify a specific field. No bookings, closures, waitlists, scores or team records are seeded. The February Spirit closure in the deck is not a September closure. All slots begin empty. Seed operations insert missing records in one transaction, preserve existing records, and can be repeated. Use new `--start-date` values for later demonstrations.

The frontend still has separate sample court counts, Basketball and hard-coded availability. Catalogue integration must reconcile these with the database in a later milestone; the frontend is not yet connected to the backend.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests require PostgreSQL. They use the configured database (or `TEST_DATABASE_URL` when provided), create randomly named `test_slotgrab_*` schemas and remove only those schemas afterward. They never delete public application tables. Use a development database with CREATE SCHEMA permission. Coverage includes seed repeatability, booking uniqueness, cancellation/rebooking, foreign keys, input constraints, idempotency-key uniqueness, health success/failure and Swagger/OpenAPI. This is not the later 50-request booking API race test.

## Phase 2: read-only catalogue

| Endpoint | Behaviour |
| --- | --- |
| `GET /api/sports` | All sports ordered by name then ID; includes sports without facilities |
| `GET /api/facilities?sport_id=1` | Active facilities for that sport, ordered by location/name/ID |
| `GET /api/slots?facility_id=1&date=2026-09-25` | Only that facility/date's slots, ordered by start time/ID |

Use IDs returned by the API; do not assume seeded IDs. Unknown sport/facility returns 404; existing parent with no facilities/slots returns 200 and `[]`. Required IDs must be positive and within PostgreSQL bigint range; missing/invalid IDs or dates return 422. Connection/query failures return generic 503. Success responses use `Cache-Control: no-store`.

Slot response example (IDs illustrative):

```json
{"id":101,"facility_id":1,"date":"2026-09-25","start_time":"18:00:00","end_time":"19:00:00","status":"AVAILABLE"}
```

All times mean IST. Status is computed from the current database snapshot:

1. Inactive facility or slot start at/before current IST time: `UNAVAILABLE` (even if historically booked).
2. Otherwise, a CONFIRMED booking exists: `BOOKED`.
3. Otherwise: `AVAILABLE`. CANCELLED bookings never block availability.

The API does not return booking/user identities. Status is not persisted. A later booking API must recheck availability transactionally; a successful read does not reserve anything. Public catalogue reads do not require login. This phase adds no booking/cancellation endpoint, CORS policy, frontend integration, closures or waitlist backend.

### Manual Swagger checklist

Open http://127.0.0.1:8000/docs and use Try it out / Execute:

1. `/api/sports`: expect Badminton, Football, Tennis; record their IDs.
2. `/api/facilities` with Badminton's ID: expect 10 courts (6 Old SAC, 4 New SAC). Tennis: 1. Football: empty list.
3. `/api/slots` with a returned court ID and `2026-09-25`: expect 5 one-hour slots, starting 16:00 through 20:00. Repeat for September 26. Future empty slots are AVAILABLE; after their start they are UNAVAILABLE.
4. Use an unseeded date such as `2099-10-01`: expect `[]`, not an error.
5. Unknown positive ID: expect 404. Zero/negative/non-integer ID, missing date, or `2026-02-30`: expect 422.
6. `/health`: expect 200 and database connected. The frontend will still show demo data until its integration milestone.

Confirmed-to-cancelled availability changes and inactive-facility filtering are covered by `tests/test_catalogue.py` in isolated schemas. Run tests to verify these without manually changing shared demo data. Restart Uvicorn after editing Python files, or use `--reload` during development.

## Phase 3: atomic booking API

The booking route is a local demo until real authentication exists. It is **disabled by default**. Start it from `backend/` in a local PowerShell terminal:

```powershell
$env:SLOTGRAB_DEMO_MODE = '1'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The demo routes also check the request's peer address and reject non-local peers. Never enable demo mode on a public or reverse-proxied deployment. `X-Demo-User-Id` selects a synthetic seed identity; it is **not login or institute verification**. Production booking must replace it with authenticated identity. Only seed users are shown by `GET /api/demo/users` while demo mode is on; the endpoint returns IDs and synthetic names without email addresses.

`POST /api/bookings` takes a JSON body such as:

```json
{"slot_id":101,"idempotency_key":"e68ba042-0052-4dc4-9b04-74e0867ca397"}
```

The `X-Demo-User-Id` request header must be a positive ID from `/api/demo/users`. Use a fresh UUID for every new booking attempt; reuse the same UUID only to retry the same attempted booking. Results:

| HTTP | Meaning |
| --- | --- |
| `201` | New booking committed; body contains booking ID, slot ID, CONFIRMED status and creation time |
| `200` | Same user's same key and slot already succeeded; original booking returned without a new row |
| `409 SLOT_ALREADY_BOOKED` | Another confirmed booking owns the slot |
| `409 SLOT_UNAVAILABLE` | Facility inactive or slot already started in IST |
| `409 IDEMPOTENCY_KEY_REUSED` | Same user's key was used for a different slot |
| `409 REQUEST_ALREADY_CANCELLED` | Original booking was cancelled; new attempt needs a fresh key |
| `401` | Missing/unknown demo identity |
| `403` | Demo mode off or peer not local |
| `404` | Unknown slot ID |
| `422` | Invalid header, slot ID or UUID |
| `503` | Database unavailable |

Each request uses one SQLAlchemy transaction. A blocking PostgreSQL `FOR UPDATE` lock on the slot and its facility serializes contenders, followed by an active-facility and IST start-time check, a confirmed-booking check, and one insert. The partial unique index on confirmed bookings remains a second database guarantee. An `IntegrityError` from a simultaneous key/slot collision is resolved to an existing idempotent response or a conflict. The API returns success only after commit. The catalogue is a snapshot, so its AVAILABLE label does not reserve a slot.

### Manual Swagger tests

1. Open `/docs`, call `GET /api/demo/users` and note two different synthetic IDs.
2. Call `GET /api/sports`, choose Badminton, then `GET /api/facilities`, then `GET /api/slots` for a future date such as `2026-09-25`. Note an AVAILABLE slot ID. If testing after that date, seed new days with `python -m app.seed --start-date YYYY-MM-DD --days 2` first.
3. In `POST /api/bookings`, use the first synthetic ID as the `X-Demo-User-Id` header and a fresh UUID in the JSON body. Expect `201` and a booking ID.
4. Call `GET /api/slots` again: that slot must show BOOKED. Repeat the exact POST with the same user, slot and UUID: expect `200` and the same booking ID.
5. Repeat with the second user and a different UUID: expect `409 SLOT_ALREADY_BOOKED`. Use the first user's original UUID on a different available slot: expect `409 IDEMPOTENCY_KEY_REUSED`.
6. Try an unknown slot ID (`999999`): expect `404`. Try an already-started slot or disable a facility in the test database: expect `409 SLOT_UNAVAILABLE`.

Use another free slot or seed a future date to repeat tests. Do not remove bookings by hand merely to reset a shared demo. There is no cancellation HTTP endpoint or frontend connection yet; those remain later milestones. `tests/test_bookings.py` runs 50 simultaneous users against one slot in an isolated PostgreSQL schema: exactly one request returns 201, 49 return 409, and the database contains one confirmed row. It also tests same-key retries, conflicting keys/slots, access guards and invalid requests.
