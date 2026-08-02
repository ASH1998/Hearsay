import type { Metadata } from "next";

import "./globals.css";

const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ??
  "https://hearsay.ashutoshmishra.dev";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "Hearsay — Greyhaven remembers",
  description:
    "A social-memory game where every promise, rumor, and vote has a history.",
  openGraph: {
    title: "Hearsay — Two histories, one election",
    description:
      "Replay two completed runs inside Greyhaven and see how remembered choices change the vote.",
    images: [{ url: "/og.png", width: 1536, height: 1024, alt: "Hearsay recorded runs" }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Hearsay — Two histories, one election",
    description:
      "Replay two completed runs and see how Greyhaven's memories change the vote.",
    images: ["/og.png"],
  },
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
