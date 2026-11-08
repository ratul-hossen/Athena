import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Athina Admin - Companion Dashboard",
  description: "Personality, Memory & Infrastructure Management for Athina",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-black text-athina-text min-h-screen">
        {children}
      </body>
    </html>
  );
}
