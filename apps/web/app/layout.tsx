import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Hearsay — Greyhaven remembers",
  description:
    "A social-memory game where every promise, rumor, and vote has a history.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
