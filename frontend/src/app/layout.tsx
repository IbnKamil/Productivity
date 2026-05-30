import type { Metadata } from "next";
import Link from "next/link";
import { ReactNode } from "react";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Tunnel Tasks",
  description: "Break goals into one visible micro-task at a time."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="min-h-screen">
            <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6 text-sm text-slate-300">
              <Link href="/" className="font-semibold tracking-wide text-white">
                Tunnel Tasks
              </Link>
              <nav className="flex gap-4">
                <Link href="/goals/new">New goal</Link>
                <Link href="/stats">Stats</Link>
                <Link href="/settings">Settings</Link>
              </nav>
            </header>
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}
