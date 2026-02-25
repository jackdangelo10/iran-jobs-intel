import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Iran Jobs Intelligence",
  description: "Dashboard for Iranian job market data",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100">
        <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.18),_transparent_45%),radial-gradient(circle_at_20%_20%,_rgba(239,68,68,0.12),_transparent_40%),linear-gradient(180deg,_rgba(2,6,23,0.9),_rgba(2,6,23,1))]" />
        <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur relative">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-3">
            <div className="w-10 h-7 rounded-sm overflow-hidden shadow-lg border border-slate-700 bg-white">
              <svg
                viewBox="0 0 30 20"
                className="w-full h-full"
                aria-label="Iranian flag"
                role="img"
              >
                <rect width="30" height="20" fill="#ffffff" />
                <rect width="30" height="6.7" y="0" fill="#239f40" />
                <rect width="30" height="6.7" y="13.3" fill="#da0000" />
                <circle cx="15" cy="10" r="2.2" fill="#d4af37" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-slate-100">
                Iran Jobs Intelligence
              </h1>
              <p className="text-xs text-slate-400">
                Job market analytics dashboard
              </p>
            </div>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
