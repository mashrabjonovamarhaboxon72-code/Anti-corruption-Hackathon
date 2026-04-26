import type { Metadata } from "next";
import { AuthProvider } from "@/contexts/AuthContext";
import { BroadcastProvider } from "@/contexts/BroadcastContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "Integrity Shield",
  description: "Anonymous corruption-reporting transparency dashboard.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <BroadcastProvider>
          <AuthProvider>{children}</AuthProvider>
        </BroadcastProvider>
      </body>
    </html>
  );
}
