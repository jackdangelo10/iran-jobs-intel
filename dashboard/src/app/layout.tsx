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
      <body className="min-h-screen bg-slate-900 text-slate-100">
        <header className="border-b border-slate-700 bg-slate-800/50 backdrop-blur">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-3">
            <div className="w-8 h-8 rounded-md bg-emerald-500 flex items-center justify-center text-slate-900 font-bold text-sm">
              IJ
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
