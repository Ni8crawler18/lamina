"use client";

import localFont from "next/font/local";
import "./globals.css";
import Link from "next/link";
import { usePathname } from "next/navigation";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="28" height="28" rx="8" fill="#8259ef" />
      <path
        d="M8 9.5h4.5v9H8v-2.25h2.25v-4.5H8V9.5zM15.5 9.5H20v2.25h-2.25v4.5H20v2.25h-4.5v-9z"
        fill="white"
      />
    </svg>
  );
}

function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[220px] bg-card/40 border-r border-border/50 flex flex-col h-screen fixed left-0 top-0 z-50">
      <div className="p-5">
        <Link href="/" className="flex items-center gap-2.5">
          <Logo />
          <span className="font-semibold text-[15px] tracking-tight">Lamina</span>
        </Link>
      </div>

      <nav className="flex-1 px-3 mt-2 space-y-0.5">
        <NavLink href="/" label="Dashboard" active={pathname === "/"} icon={
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
        } />
        <NavLink href="/chat" label="Agent" active={pathname === "/chat"} icon={
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 011.037-.443 48.282 48.282 0 005.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
        } />
      </nav>

      <div className="p-4 mx-3 mb-3 rounded-lg bg-secondary/40 border border-border/30">
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Hedera Testnet
        </div>
        <p className="font-mono text-[11px] text-muted-foreground/60 mt-1">0.0.8003096</p>
      </div>
    </aside>
  );
}

function NavLink({ href, label, active, icon }: { href: string; label: string; active: boolean; icon: React.ReactNode }) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] transition-all duration-150 ${
        active
          ? "text-foreground bg-primary/10 border border-primary/20"
          : "text-muted-foreground hover:text-foreground hover:bg-secondary/50 border border-transparent"
      }`}
    >
      <svg className={`w-[18px] h-[18px] flex-shrink-0 ${active ? "text-primary" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        {icon}
      </svg>
      {label}
    </Link>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <title>Lamina</title>
        <meta name="description" content="Autonomous RWA lifecycle agent on Hedera" />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <Sidebar />
        <main className="ml-[220px] min-h-screen bg-dots">
          {children}
        </main>
      </body>
    </html>
  );
}
