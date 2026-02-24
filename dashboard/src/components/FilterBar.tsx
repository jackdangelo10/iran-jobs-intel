"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

const DATE_RANGES = [
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
  { value: "all", label: "All time" },
];

const SITES = [
  { value: "all", label: "All Sites" },
  { value: "irantalent", label: "IranTalent" },
  { value: "jobinja", label: "Jobinja" },
  { value: "jobvision", label: "JobVision" },
];

export default function FilterBar() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentSite = searchParams.get("site") || "all";
  const currentRange = searchParams.get("range") || "30";

  const updateParam = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set(key, value);
      router.push(`?${params.toString()}`);
    },
    [router, searchParams]
  );

  return (
    <div className="flex flex-wrap gap-3 items-center">
      <div className="flex items-center gap-2">
        <label className="text-sm text-slate-400 whitespace-nowrap">
          Date range
        </label>
        <select
          value={currentRange}
          onChange={(e) => updateParam("range", e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          {DATE_RANGES.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <label className="text-sm text-slate-400 whitespace-nowrap">
          Source site
        </label>
        <select
          value={currentSite}
          onChange={(e) => updateParam("site", e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          {SITES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {(currentSite !== "all" || currentRange !== "30") && (
        <button
          onClick={() => router.push("?")}
          className="text-xs text-slate-400 hover:text-slate-200 underline"
        >
          Reset filters
        </button>
      )}
    </div>
  );
}
