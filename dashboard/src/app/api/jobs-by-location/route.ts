import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const site = searchParams.get("site") || "all";
  const range = searchParams.get("range") || "30";

  const days = range === "all" ? 36500 : parseInt(range, 10);
  const sql = getDb();

  try {
    const rows = await sql`
      SELECT
        COALESCE(location_raw, 'Unknown') AS location,
        COUNT(*)::int AS count
      FROM job_postings
      WHERE (${site} = 'all' OR source_site = ${site})
        AND first_seen_date >= CURRENT_DATE - (${days}::int)
        AND location_raw IS NOT NULL
        AND location_raw != ''
      GROUP BY location_raw
      ORDER BY count DESC
      LIMIT 15
    `;

    return NextResponse.json(rows);
  } catch (error) {
    console.error("/api/jobs-by-location error:", error);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
