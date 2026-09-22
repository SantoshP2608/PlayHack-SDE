import test from "node:test";
import assert from "node:assert/strict";
import { createDemoState, changeDemoState, getSlotStatus, slotKey } from "../lib/demo-bookings.mjs";

const selection = { sport: "Badminton", court: 1, day: "2026-09-25", time: 2 };

test("a repeat click cannot create duplicate local bookings", () => {
  let state = changeDemoState(createDemoState(), { type: "book", selection });
  state = changeDemoState(state, { type: "book", selection });
  assert.equal(state.bookings.length, 1);
  assert.equal(getSlotStatus(state, selection), "yours");
  state = changeDemoState(state, { type: "cancel", key: slotKey(selection) });
  assert.equal(getSlotStatus(state, selection), "available");
});

test("a conflict offers a waitlist without creating a booking", () => {
  let state = changeDemoState(createDemoState(), { type: "conflict", selection });
  state = changeDemoState(state, { type: "book", selection });
  assert.equal(state.bookings.length, 0);
  state = changeDemoState(state, { type: "join", selection });
  state = changeDemoState(state, { type: "join", selection });
  assert.equal(state.waitlist.length, 1);
  assert.equal(getSlotStatus(state, selection), "waiting");
  state = changeDemoState(state, { type: "leave", key: slotKey(selection) });
  assert.equal(getSlotStatus(state, selection), "booked");
});

test("slot identity distinguishes facilities and days", () => {
  const state = changeDemoState(createDemoState(), { type: "book", selection });
  assert.equal(getSlotStatus(state, { ...selection, court: 2 }), "available");
  assert.equal(getSlotStatus(state, { ...selection, day: "2026-09-26" }), "available");
});
