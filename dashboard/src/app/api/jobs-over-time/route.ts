import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const site = searchParams.get("site") || "all";
  const range = searchParams.get("range") || "30";

  const days = range === "all" ? 365 : parseInt(range, 10);
  const sql = getDb();

  try {
    const rows = await sql`
      SELECT
        first_seen_date::text AS date,
        source_site,
        COUNT(*)::int AS count
      FROM job_postings
      WHERE (${site} = 'all' OR source_site = ${site})
        AND first_seen_date >= CURRENT_DATE - ${days}
      GROUP BY first_seen_date, source_site
      ORDER BY first_seen_date ASC
    `;

    return NextResponse.json(rows);
  } catch (error) {
    console.error("/api/jobs-over-time error:", error);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
