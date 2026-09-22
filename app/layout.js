import "./globals.css";

export const metadata = {
  title: "SlotGrab | Find your next game",
  description: "Explore campus courts, book a session, or join a waitlist.",
};

export default function RootLayout({ children }) {
  return <html lang="en"><body>{children}</body></html>;
}
