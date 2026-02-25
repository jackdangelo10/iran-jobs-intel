import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export const dynamic = "force-dynamic";

function toInt(value: string | null, fallback: number) {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const site = searchParams.get("site") || "all";
  const range = searchParams.get("range") || "30";
  const query = searchParams.get("q") || "";
  const company = searchParams.get("company") || "";
  const location = searchParams.get("location") || "";
  const employment = searchParams.get("employment") || "all";
  const experience = searchParams.get("experience") || "all";
  const activeOnly = (searchParams.get("active") || "true") === "true";

  const page = toInt(searchParams.get("page"), 1);
  const pageSize = Math.min(toInt(searchParams.get("page_size"), 20), 100);
  const offset = (page - 1) * pageSize;

  const days = range === "all" ? null : toInt(range, 30);
  const sql = getDb();

  const conditions = [];

  if (site !== "all") {
    conditions.push(sql`source_site = ${site}`);
  }
  if (days !== null) {
    conditions.push(sql`first_seen_date >= CURRENT_DATE - (${days}::int)`);
  }
  if (activeOnly) {
    conditions.push(sql`is_active = TRUE`);
  }
  if (company.trim().length > 0) {
    conditions.push(sql`company_name_raw ILIKE ${`%${company}%`}`);
  }
  if (location.trim().length > 0) {
    conditions.push(sql`location_raw ILIKE ${`%${location}%`}`);
  }
  if (employment !== "all") {
    conditions.push(sql`employment_type = ${employment}`);
  }
  if (experience !== "all") {
    conditions.push(sql`experience_level = ${experience}`);
  }
  if (query.trim().length > 0) {
    const q = `%${query}%`;
    conditions.push(
      sql`(
        title_persian ILIKE ${q}
        OR title_english ILIKE ${q}
        OR description_persian ILIKE ${q}
        OR description_english ILIKE ${q}
      )`
    );
  }

  const where =
    conditions.length > 0
      ? sql`WHERE ${sql.join(conditions, sql` AND `)}`
      : sql``;

  try {
    const rows = await sql`
      SELECT
        id,
        source_site,
        source_url,
        title_persian,
        title_english,
        description_persian,
        description_english,
        company_name_raw,
        company_url,
        location_raw,
        employment_type,
        experience_level,
        posted_date,
        first_seen_date,
        last_seen_date,
        is_active,
        processing_status,
        (title_english IS NOT NULL OR description_english IS NOT NULL) AS has_english
      FROM job_postings
      ${where}
      ORDER BY COALESCE(posted_date, first_seen_date) DESC, first_seen_date DESC, id DESC
      LIMIT ${pageSize} OFFSET ${offset}
    `;

    const total = await sql`
      SELECT COUNT(*)::int AS count
      FROM job_postings
      ${where}
    `;

    return NextResponse.json({
      page,
      page_size: pageSize,
      total: total[0]?.count ?? 0,
      rows,
    });
  } catch (error) {
    console.error("/api/jobs error:", error);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }
}
