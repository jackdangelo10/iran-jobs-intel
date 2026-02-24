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
    const [employmentType, experienceLevel, sourceSite] = await Promise.all([
      sql`
        SELECT
          COALESCE(employment_type, 'unknown') AS label,
          COUNT(*)::int AS count
        FROM job_postings
        WHERE (${site} = 'all' OR source_site = ${site})
          AND first_seen_date >= CURRENT_DATE - ${days}
        GROUP BY employment_type
        ORDER BY count DESC
      `,
      sql`
        SELECT
          COALESCE(experience_level, 'unknown') AS label,
          COUNT(*)::int AS count
        FROM job_postings
        WHERE (${site} = 'all' OR source_site = ${site})
          AND first_seen_date >= CURRENT_DATE - ${days}
        GROUP BY experience_level
        ORDER BY count DESC
      `,
      sql`
        SELECT
          source_site AS label,
          COUNT(*)::int AS count
        FROM job_postings
        WHERE (${site} = 'all' OR source_site = ${site})
          AND first_seen_date >= CURRENT_DATE - ${days}
        GROUP BY source_site
        ORDER BY count DESC
      `,
    ]);

    return NextResponse.json({
      employmentType,
      experienceLevel,
      sourceSite,
    });
  } catch (error) {
    console.error("/api/breakdowns error:", error);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
