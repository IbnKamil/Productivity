import type { Metadata } from "next";
import Link from "next/link";
import { ReactNode } from "react";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Туннельные задачи",
  description: "Разбивайте цели на микро-задачи и видьте только следующий шаг."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="min-h-screen">
            <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6 text-sm text-slate-300">
              <Link href="/" className="font-semibold tracking-wide text-white">
                Туннельные задачи
              </Link>
              <nav className="flex gap-4">
                <Link href="/goals/new">Новая цель</Link>
                <Link href="/stats">Статистика</Link>
                <Link href="/settings">Настройки</Link>
              </nav>
            </header>
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}
