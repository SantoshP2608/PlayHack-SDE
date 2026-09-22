"use client";

import { useReducer, useRef, useState } from "react";
import { changeDemoState, createDemoState, days, getSlotStatus, slotKey, slots, sports } from "../lib/demo-bookings.mjs";

const statusLabels = { available: "Available", booked: "Booked", yours: "Your booking", waiting: "Waitlisted" };

export default function SlotGrab() {
  const [selection, setSelection] = useState({ sport: "Badminton", court: 1, day: days[0].id, time: 2 });
  const [state, dispatch] = useReducer(changeDemoState, undefined, createDemoState);
  const [view, setView] = useState("explore");
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const requestPending = useRef(false);
  const [demoOutcome, setDemoOutcome] = useState("success");
  const [cancelKey, setCancelKey] = useState(null);
  const status = getSlotStatus(state, selection);
  const day = days.find((entry) => entry.id === selection.day);
  const wait = state.waitlist.find((entry) => entry.key === slotKey(selection));
  const recordCount = state.bookings.length + state.waitlist.length;

  function choose(patch) {
    setSelection((current) => ({ ...current, ...patch }));
    setNotice(null);
  }

  function navigate(next) {
    setView(next);
    setNotice(null);
    setCancelKey(null);
  }

  async function submit() {
    if (requestPending.current) return;
    setNotice(null);
    if (status === "yours") return navigate("bookings");
    if (status === "waiting") {
      dispatch({ type: "leave", selection });
      return setNotice({ title: "You’ve left the waitlist", text: "Choose another time, or join again later." });
    }
    if (status === "booked") {
      dispatch({ type: "join", selection });
      return setNotice({ title: "You’re #3 on the waitlist", text: "Two sample players are ahead of you. You don’t have a booking yet." });
    }

    // Simulates latency for UI review. Replace this with a server request later.
    requestPending.current = true;
    setBusy(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 650));
      if (demoOutcome === "conflict") {
        dispatch({ type: "conflict", selection });
        setNotice({ warning: true, title: "This slot was just booked", text: "Another booking was confirmed first. Join the waitlist, or choose another available time." });
      } else if (demoOutcome === "error") {
        setNotice({ warning: true, title: "We couldn’t complete your request", text: "This simulated request failed without creating a booking. Try again when you’re ready." });
      } else {
        dispatch({ type: "book", selection });
        setNotice({ title: "Your court is booked", text: `${selection.sport} Court ${selection.court} · ${day.label} · ${slots[selection.time].range}. Find it in My bookings.` });
      }
    } finally {
      requestPending.current = false;
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="site-header">
        <div className="brand"><span className="brand-mark" aria-hidden="true">S</span>SlotGrab <span className="campus">IIT GUWAHATI</span></div>
        <nav aria-label="Main navigation" className="flex items-center gap-7">
          <button disabled={busy} aria-current={view === "explore" ? "page" : undefined} onClick={() => navigate("explore")}>Explore courts</button>
          <button disabled={busy} aria-current={view === "bookings" ? "page" : undefined} onClick={() => navigate("bookings")}>My bookings <span className="count">{recordCount}</span></button>
        </nav>
      </header>

      <main id="main" className="mx-auto w-full max-w-6xl px-5 py-8 sm:px-8 lg:px-10">
        {view === "explore" ? <>
          <section className="hero">
            <div><span className="eyebrow">LESS PLANNING. MORE PLAYING.</span><h1>Your next game<br />starts here.</h1><p>A court, an hour, and something to look forward to.</p></div>
            <div className="court-art" aria-hidden="true"><div className="court-lines" /><span>MAKE TIME TO PLAY.</span></div>
          </section>

          <div className="filters">
            <div className="flex flex-wrap gap-2" aria-label="Choose a sport">
              {sports.map((sport) => <button key={sport} className="sport-button" disabled={busy} aria-pressed={selection.sport === sport} onClick={() => choose({ sport, court: 1 })}>{sport}</button>)}
            </div>
            <label className="flex flex-wrap items-center gap-3 text-sm text-muted">Choose a day<select disabled={busy} value={selection.day} onChange={(event) => choose({ day: event.target.value })}>{days.map((date) => <option key={date.id} value={date.id}>{date.label}</option>)}</select></label>
          </div>

          <div className="grid items-start gap-7 lg:grid-cols-[1.08fr_1fr]">
            <section aria-labelledby="facilities-heading">
              <div className="section-title"><h2 id="facilities-heading">Find your court</h2><span>Old SAC · Sample facilities</span></div>
              {[1, 2, 3].map((court) => {
                const free = slots.filter((_, time) => getSlotStatus(state, { ...selection, court, time }) === "available").length;
                return <button key={court} className="court-button" disabled={busy} aria-pressed={selection.court === court} onClick={() => choose({ court })}>
                  <span className="court-number">0{court}</span><span className="min-w-0"><strong>{selection.sport} Court {court}</strong><small>Old SAC · {selection.sport === "Badminton" ? "Indoor" : "Outdoor"}</small></span><span className="availability">{free} slots free <span aria-hidden="true">↗</span></span>
                </button>;
              })}
              <aside className="help"><strong>Your preferred slot already booked?</strong><p>Join its waitlist. Places are assigned in the order people join.</p></aside>
            </section>

            <section className="booking-panel" aria-labelledby="session-heading" aria-busy={busy}>
              <div className="flex items-center justify-between gap-3 mb-4"><span className="eyebrow">YOUR SESSION</span><span className="duration">60 minutes</span></div>
              <h2 id="session-heading">{selection.sport} Court {selection.court}</h2><p className="text-sm">Old SAC · {selection.sport === "Badminton" ? "Indoor" : "Outdoor"}</p>
              <hr /><div className="section-title"><h3>Select a time</h3><span>All times IST</span></div>
              <div className="grid grid-cols-3 gap-2">
                {slots.map((slot, time) => {
                  const slotStatus = getSlotStatus(state, { ...selection, time });
                  return <button key={time} className="slot-button" disabled={busy} data-status={slotStatus} aria-pressed={selection.time === time} aria-label={`${slot.range}, ${statusLabels[slotStatus]}`} onClick={() => choose({ time })}>{slot.start}<small>{statusLabels[slotStatus]}</small></button>;
                })}
              </div>
              <p className="slot-hint">Booked slots are selectable for the waitlist.</p>
              <div className="selection-summary" aria-live="polite"><strong>{day.full} · {slots[selection.time].range}</strong><span>{status === "yours" ? "This court is reserved for you." : status === "waiting" ? `Waitlist position #${wait.position} · No booking yet.` : status === "booked" ? "Booked · Join the first-come waitlist." : "Available · One booking reserves this court."}</span></div>
              <div aria-live="polite" aria-atomic="true">{notice && <div className={`notice ${notice.warning ? "warning" : ""}`}><strong>{notice.title}</strong><span>{notice.text}</span></div>}</div>
              <button className="primary-button" disabled={busy} onClick={submit}>{busy ? "Checking availability…" : status === "yours" ? "View my booking →" : status === "waiting" ? "Leave waitlist" : status === "booked" ? "Join waitlist →" : "Book this slot →"}</button>
              <p className="action-note">{status === "booked" || status === "waiting" ? "Joining the waitlist does not confirm a booking." : status === "yours" ? "Your session appears in My bookings." : "You’ll see a confirmation when your booking succeeds."}</p>
            </section>
          </div>
        </> : <section aria-labelledby="bookings-heading">
          <span className="eyebrow">YOUR TIME TO PLAY</span><h1 id="bookings-heading">My bookings</h1><p>Confirmed sessions and the slots you’re waiting for.</p>
          <div className="my-records">
            {recordCount === 0 && <div className="record"><div><h2>Your next game is waiting.</h2><p>No bookings or waitlist entries yet.</p></div></div>}
            {[...state.bookings.map((entry) => ({ ...entry, type: "booking" })), ...state.waitlist.map((entry) => ({ ...entry, type: "waitlist" }))].map((entry) => <article className="record" key={entry.key}>
              <div><span className="badge">{entry.type === "booking" ? "✓ Confirmed" : `Waitlisted · #${entry.position}`}</span><h2>{entry.sport} Court {entry.court}</h2><p>Old SAC · {days.find((date) => date.id === entry.day).label} · {slots[entry.time].range}</p>{entry.type === "waitlist" && <p>You don’t have a booking yet.</p>}</div>
              {entry.type === "waitlist" ? <button className="secondary-button" onClick={() => dispatch({ type: "leave", key: entry.key })}>Leave waitlist</button> : cancelKey === entry.key ? <div className="cancel-confirm" role="group" aria-label="Confirm cancellation"><p>Release this slot?</p><div className="flex flex-wrap gap-2"><button className="secondary-button" onClick={() => setCancelKey(null)}>Keep booking</button><button className="secondary-button" onClick={() => { dispatch({ type: "cancel", key: entry.key }); setCancelKey(null); }}>Yes, cancel</button></div></div> : <button className="secondary-button" onClick={() => setCancelKey(entry.key)}>Cancel booking</button>}
            </article>)}
          </div><button className="secondary-button" onClick={() => navigate("explore")}>Explore courts →</button>
        </section>}

        <details className="demo-controls"><summary>Frontend demo controls</summary><div className="flex flex-wrap items-center gap-3 mt-4"><label htmlFor="demo-outcome">Next booking result</label><select id="demo-outcome" disabled={busy} value={demoOutcome} onChange={(event) => setDemoOutcome(event.target.value)}><option value="success">Success</option><option value="conflict">Slot just taken</option><option value="error">Request failed</option></select></div><p>Sample data resets when you refresh. Queue position is simulated; no real reservation, authentication, or database is connected.</p></details>
      </main>
      <footer className="flex flex-wrap justify-between gap-3"><span>SlotGrab · One platform. Zero clashes.</span><span>Frontend demo · Sample data · No real reservations</span></footer>
    </div>
  );
}
