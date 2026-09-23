# SlotGrab frontend

Backend foundation, Phase 2 catalogue endpoints, SQLAlchemy models, seed provenance and Swagger test instructions are in [backend/README.md](backend/README.md). Read [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) before contributing. The frontend below is still a standalone demo and is not connected to the backend yet.

Campus Club UI using Next.js 16, JavaScript, React and Tailwind CSS 4. Sign-in is deferred.

## Run on Windows

Open this folder in your editor. In its PowerShell terminal:

```powershell
npm.cmd install
npm.cmd run dev
```

Open http://localhost:3000. Stop with Ctrl+C. Use `npm.cmd` if PowerShell blocks `npm.ps1`.

Node.js 20.9 or newer is required; this computer currently has Node 24 installed.

## Files to learn first

| File | Purpose |
| --- | --- |
| `app/page.js` | Home route; loads the main interface |
| `components/SlotGrab.js` | Main screen, event handlers, booking and waitlist feedback |
| `app/globals.css` | Campus Club colors, typography, responsive styles and Tailwind import |
| `lib/demo-bookings.mjs` | Sample sports, dates, slots and local state transitions |
| `app/layout.js` | Shared HTML layout and page title |
| `postcss.config.mjs` | Tailwind CSS compiler setup |
| `package.json` | Dependencies and commands |
| `tests/demo-bookings.test.mjs` | Local booking and waitlist state checks |

## Try these flows

1. Select a free slot and book it. Open My bookings.
2. Select a booked slot, join its waitlist, then leave it.
3. Cancel your own booking and check that its slot is free again.
4. Expand Frontend demo controls. Set Next booking result to Slot just taken, select a free slot and book. The result should offer a waitlist without creating a booking.
5. Set the demo result to Request failed, select a free slot, and book. No record should be created.
6. Resize the browser to a phone width and try the same flows.

```powershell
npm.cmd test
npm.cmd run build
```

## Current boundaries

This is a frontend prototype, not a live booking system. Sample dates, facilities, hours and queue positions are unverified. State is in memory and resets on refresh. No sign-in, database, API, cross-user coordination, waitlist promotion, notifications or institutional access is implemented. A sample queue always starts with two people ahead.

The reducer prevents duplicate local clicks; this is not evidence of concurrent database correctness. Later, the backend must enforce one booking per facility/time slot, assign authenticated identities, maintain the first-come queue, process cancellation/promotion atomically, and return authoritative booking/conflict responses. UI success must follow that response. Real network timeouts need reconciliation/idempotency before retrying because a server may have accepted a request before the connection failed.

The separate 50-request concurrency demonstration belongs to backend integration, not these UI tests.

## Learning and next steps

Start by changing one heading in `components/SlotGrab.js` and observing the automatic browser update. Change sample data in `lib/demo-bookings.mjs` only after confirming facilities and rules. Keep the approved green design in `app/globals.css`.

Official setup references: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation) and [Tailwind with Next.js](https://tailwindcss.com/docs/installation/framework-guides/nextjs).
