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
        s.skill_name_english AS skill,
        COUNT(*)::int AS count
      FROM job_skills js
      JOIN skills s ON s.id = js.skill_id
      JOIN job_postings jp ON jp.id = js.job_posting_id
      WHERE (${site} = 'all' OR jp.source_site = ${site})
        AND jp.first_seen_date >= CURRENT_DATE - ${days}
      GROUP BY s.skill_name_english
      ORDER BY count DESC
      LIMIT 15
    `;

    return NextResponse.json(rows);
  } catch (error) {
    console.error("/api/top-skills error:", error);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
