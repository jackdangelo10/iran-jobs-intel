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
        COUNT(*)::int AS total_jobs,
        COUNT(*) FILTER (WHERE is_active = true)::int AS active_jobs,
        COUNT(DISTINCT company_id) FILTER (WHERE company_id IS NOT NULL)::int AS companies,
        COUNT(*) FILTER (WHERE first_seen_date >= CURRENT_DATE - 7)::int AS new_this_week
      FROM job_postings
      WHERE (${site} = 'all' OR source_site = ${site})
        AND first_seen_date >= CURRENT_DATE - (${days}::int)
    `;

    return NextResponse.json(rows[0]);
  } catch (error) {
    console.error("/api/stats error:", error);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
