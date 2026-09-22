// Browser-only sample data. This module provides NO database or concurrency guarantee.
export const sports = ["Badminton", "Tennis", "Basketball"];
export const courtCounts = { Badminton: 5, Tennis: 4, Basketball: 2 };
export const slots = [
  { start: "4:00 PM", range: "4:00–5:00 PM" },
  { start: "5:00 PM", range: "5:00–6:00 PM" },
  { start: "6:00 PM", range: "6:00–7:00 PM" },
  { start: "7:00 PM", range: "7:00–8:00 PM" },
  { start: "8:00 PM", range: "8:00–9:00 PM" },
  { start: "9:00 PM", range: "9:00–10:00 PM" },
];
export const days = [
  { id: "2026-09-25", label: "Fri, 25 Sep", full: "Friday, 25 September" },
  { id: "2026-09-26", label: "Sat, 26 Sep", full: "Saturday, 26 September" },
];

export function slotKey(selection) {
  return `${selection.sport}|${selection.court}|${selection.day}|${selection.time}`;
}

export function createDemoState() {
  return { bookings: [], waitlist: [], taken: [] };
}

export function getSlotStatus(state, selection) {
  const key = slotKey(selection);
  if (state.bookings.some((entry) => entry.key === key)) return "yours";
  if (state.waitlist.some((entry) => entry.key === key)) return "waiting";
  if (state.taken.includes(key) || selection.time === 1 || selection.time === 4 || (selection.court === 3 && selection.time === 0)) return "booked";
  return "available";
}

export function changeDemoState(state, action) {
  const selection = action.selection;
  const key = selection ? slotKey(selection) : action.key;
  switch (action.type) {
    case "book":
      if (getSlotStatus(state, selection) !== "available") return state;
      return { ...state, bookings: [...state.bookings, { ...selection, key }] };
    case "join":
      if (getSlotStatus(state, selection) !== "booked") return state;
      // Two sample users are ahead. Real queue position must come from the API.
      return { ...state, waitlist: [...state.waitlist, { ...selection, key, position: 3 }] };
    case "leave":
      return { ...state, waitlist: state.waitlist.filter((entry) => entry.key !== key) };
    case "cancel":
      return { ...state, bookings: state.bookings.filter((entry) => entry.key !== key) };
    case "conflict":
      if (getSlotStatus(state, selection) !== "available") return state;
      return { ...state, taken: [...state.taken, key] };
    default:
      return state;
  }
}
