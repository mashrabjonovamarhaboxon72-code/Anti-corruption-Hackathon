import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Conflict-of-Interest Detector — openinfo.uz",
  description: "Detect conflicts of interest across Uzbek company boards by matching names.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
