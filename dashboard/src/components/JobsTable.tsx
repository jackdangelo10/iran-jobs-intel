"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

type JobRow = {
  id: number;
  source_site: string;
  source_url: string;
  title_persian: string | null;
  title_english: string | null;
  description_persian: string | null;
  description_english: string | null;
  company_name_raw: string | null;
  company_url: string | null;
  location_raw: string | null;
  employment_type: string | null;
  experience_level: string | null;
  posted_date: string | null;
  first_seen_date: string | null;
  last_seen_date: string | null;
  is_active: boolean;
  processing_status: string | null;
  has_english: boolean;
};

const EMPLOYMENT_TYPES = [
  { value: "all", label: "All types" },
  { value: "full-time", label: "Full-time" },
  { value: "part-time", label: "Part-time" },
  { value: "contract", label: "Contract" },
  { value: "internship", label: "Internship" },
  { value: "temporary", label: "Temporary" },
];

const EXPERIENCE_LEVELS = [
  { value: "all", label: "All levels" },
  { value: "entry", label: "Entry" },
  { value: "mid", label: "Mid" },
  { value: "senior", label: "Senior" },
  { value: "lead", label: "Lead" },
  { value: "manager", label: "Manager" },
];

const LANGUAGE_OPTIONS = [
  { value: "en", label: "English" },
  { value: "fa", label: "Persian" },
];

function formatDate(value: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(date);
}

function formatSite(value: string) {
  if (value === "irantalent") return "IranTalent";
  if (value === "jobinja") return "Jobinja";
  if (value === "jobvision") return "JobVision";
  return value;
}

export default function JobsTable() {
  const searchParams = useSearchParams();
  const site = searchParams.get("site") || "all";
  const range = searchParams.get("range") || "30";

  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);

  const [query, setQuery] = useState("");
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [employment, setEmployment] = useState("all");
  const [experience, setExperience] = useState("all");
  const [activeOnly, setActiveOnly] = useState(true);
  const [language, setLanguage] = useState<"en" | "fa">("en");

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const qs = useMemo(() => {
    const params = new URLSearchParams();
    params.set("site", site);
    params.set("range", range);
    params.set("page", String(page));
    params.set("page_size", String(pageSize));
    params.set("active", String(activeOnly));
    if (query.trim()) params.set("q", query.trim());
    if (company.trim()) params.set("company", company.trim());
    if (location.trim()) params.set("location", location.trim());
    if (employment !== "all") params.set("employment", employment);
    if (experience !== "all") params.set("experience", experience);
    return params.toString();
  }, [
    site,
    range,
    page,
    pageSize,
    activeOnly,
    query,
    company,
    location,
    employment,
    experience,
  ]);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/jobs?${qs}`);
      const data = await res.json();
      setJobs(data.rows ?? []);
      setTotal(data.total ?? 0);
    } catch (error) {
      console.error("Failed to fetch jobs:", error);
    } finally {
      setLoading(false);
    }
  }, [qs]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  useEffect(() => {
    setPage(1);
  }, [site, range, query, company, location, employment, experience, activeOnly]);

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-[0_0_30px_rgba(16,185,129,0.08)]">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">
              Latest Job Postings
            </h2>
            <p className="text-xs text-slate-400">
              Sorted by recency with full-text search and filters
            </p>
          </div>
          <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-full p-1">
            {LANGUAGE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setLanguage(opt.value as "en" | "fa")}
                className={`px-3 py-1 text-xs rounded-full transition ${
                  language === opt.value
                    ? "bg-emerald-500 text-slate-900 font-semibold"
                    : "text-slate-300 hover:text-slate-100"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-6 gap-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search title or description"
            className="lg:col-span-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Company"
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Location"
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <select
            value={employment}
            onChange={(e) => setEmployment(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            {EMPLOYMENT_TYPES.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <select
            value={experience}
            onChange={(e) => setExperience(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            {EXPERIENCE_LEVELS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={activeOnly}
              onChange={(e) => setActiveOnly(e.target.checked)}
              className="accent-emerald-500"
            />
            Active only
          </label>
          <span className="text-slate-600">•</span>
          <span>
            Showing{" "}
            <span className="text-slate-200 font-medium">
              {(page - 1) * pageSize + 1}
            </span>{" "}
            to{" "}
            <span className="text-slate-200 font-medium">
              {Math.min(page * pageSize, total)}
            </span>{" "}
            of{" "}
            <span className="text-slate-200 font-medium">{total}</span>
          </span>
        </div>

        <div className="space-y-3">
          {loading ? (
            Array.from({ length: 6 }).map((_, index) => (
              <div
                key={index}
                className="border border-slate-800 rounded-xl p-4 bg-slate-900/50 animate-pulse"
              >
                <div className="h-4 bg-slate-800 rounded w-1/2 mb-2" />
                <div className="h-3 bg-slate-800 rounded w-1/3 mb-3" />
                <div className="h-3 bg-slate-800 rounded w-full" />
              </div>
            ))
          ) : jobs.length === 0 ? (
            <div className="text-sm text-slate-500 border border-dashed border-slate-700 rounded-xl p-6 text-center">
              No jobs match those filters.
            </div>
          ) : (
            jobs.map((job) => {
              const title =
                language === "fa"
                  ? job.title_persian || job.title_english || "—"
                  : job.title_english || job.title_persian || "—";
              const description =
                language === "fa"
                  ? job.description_persian || job.description_english || ""
                  : job.description_english || job.description_persian || "";
              const missingTranslation =
                language === "en" && !job.has_english;
              const dir = language === "fa" ? "rtl" : "ltr";

              return (
                <div
                  key={job.id}
                  className="border border-slate-800 rounded-xl p-4 bg-slate-900/40 hover:border-emerald-500/40 transition"
                >
                  <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-base font-semibold text-slate-100">
                          {title}
                        </h3>
                        {missingTranslation && (
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-200 border border-amber-500/40">
                            Not translated yet
                          </span>
                        )}
                        {!job.is_active && (
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-700 text-slate-300 border border-slate-600">
                            Inactive
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400">
                        {job.company_name_raw || "Unknown company"} •{" "}
                        {job.location_raw || "Location unknown"} •{" "}
                        {formatSite(job.source_site)}
                      </p>
                    </div>
                    <div className="text-xs text-slate-400 flex flex-wrap gap-2">
                      <span className="px-2 py-1 rounded-full bg-slate-800 border border-slate-700">
                        {job.employment_type || "Unspecified"}
                      </span>
                      <span className="px-2 py-1 rounded-full bg-slate-800 border border-slate-700">
                        {job.experience_level || "Any level"}
                      </span>
                      <span className="px-2 py-1 rounded-full bg-slate-800 border border-slate-700">
                        {formatDate(job.posted_date || job.first_seen_date)}
                      </span>
                    </div>
                  </div>
                  <p
                    dir={dir}
                    className="text-sm text-slate-300 mt-3 line-clamp-3"
                  >
                    {description || "No description available."}
                  </p>
                  <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                    <span>Last seen {formatDate(job.last_seen_date)}</span>
                    <a
                      href={job.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-emerald-300 hover:text-emerald-200"
                    >
                      View posting
                    </a>
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-3 py-1.5 text-xs rounded-lg border border-slate-700 text-slate-200 disabled:opacity-40 hover:border-emerald-500/60"
          >
            Previous
          </button>
          <div className="text-xs text-slate-400">
            Page {page} of {totalPages}
          </div>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-3 py-1.5 text-xs rounded-lg border border-slate-700 text-slate-200 disabled:opacity-40 hover:border-emerald-500/60"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
