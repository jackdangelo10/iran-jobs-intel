"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import FilterBar from "@/components/FilterBar";
import StatCard from "@/components/StatCard";
import JobsOverTimeChart from "@/components/JobsOverTimeChart";
import TopCompaniesChart from "@/components/TopCompaniesChart";
import TopSkillsChart from "@/components/TopSkillsChart";
import LocationChart from "@/components/LocationChart";
import BreakdownCharts from "@/components/BreakdownCharts";

interface Stats {
  total_jobs: number;
  active_jobs: number;
  companies: number;
  new_this_week: number;
}

interface TimePoint {
  date: string;
  source_site: string;
  count: number;
}

interface NameCount {
  company?: string;
  skill?: string;
  location?: string;
  count: number;
}

interface LabelCount {
  label: string;
  count: number;
}

interface Breakdowns {
  employmentType: LabelCount[];
  experienceLevel: LabelCount[];
  sourceSite: LabelCount[];
}

function SectionCard({
  title,
  children,
  loading,
}: {
  title: string;
  children: React.ReactNode;
  loading?: boolean;
}) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
      <h2 className="text-base font-semibold text-slate-200 mb-4">{title}</h2>
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        children
      )}
    </div>
  );
}

function DashboardContent() {
  const searchParams = useSearchParams();
  const site = searchParams.get("site") || "all";
  const range = searchParams.get("range") || "30";

  const [stats, setStats] = useState<Stats | null>(null);
  const [timeData, setTimeData] = useState<TimePoint[]>([]);
  const [companies, setCompanies] = useState<NameCount[]>([]);
  const [skills, setSkills] = useState<NameCount[]>([]);
  const [locations, setLocations] = useState<NameCount[]>([]);
  const [breakdowns, setBreakdowns] = useState<Breakdowns | null>(null);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);

  const qs = `?site=${site}&range=${range}`;

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setStatsLoading(true);

    try {
      const [
        statsRes,
        timeRes,
        companiesRes,
        skillsRes,
        locationsRes,
        breakdownsRes,
      ] = await Promise.all([
        fetch(`/api/stats${qs}`),
        fetch(`/api/jobs-over-time${qs}`),
        fetch(`/api/top-companies${qs}`),
        fetch(`/api/top-skills${qs}`),
        fetch(`/api/jobs-by-location${qs}`),
        fetch(`/api/breakdowns${qs}`),
      ]);

      const [statsData, timeData, companiesData, skillsData, locationsData, breakdownsData] =
        await Promise.all([
          statsRes.json(),
          timeRes.json(),
          companiesRes.json(),
          skillsRes.json(),
          locationsRes.json(),
          breakdownsRes.json(),
        ]);

      setStats(statsData);
      setTimeData(timeData);
      setCompanies(companiesData);
      setSkills(skillsData);
      setLocations(locationsData);
      setBreakdowns(breakdownsData);
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
    } finally {
      setLoading(false);
      setStatsLoading(false);
    }
  }, [qs]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return (
    <div className="space-y-6">
      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">
            Job Market Overview
          </h2>
          <p className="text-sm text-slate-400">
            Real-time analytics from Iranian job boards
          </p>
        </div>
        <FilterBar />
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statsLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="bg-slate-800 border border-slate-700 rounded-xl p-5 animate-pulse"
            >
              <div className="h-3 bg-slate-700 rounded w-3/4 mb-3" />
              <div className="h-8 bg-slate-700 rounded w-1/2" />
            </div>
          ))
        ) : (
          <>
            <StatCard
              label="Total Jobs Scraped"
              value={stats?.total_jobs ?? 0}
            />
            <StatCard
              label="Active Jobs"
              value={stats?.active_jobs ?? 0}
            />
            <StatCard
              label="Companies Seen"
              value={stats?.companies ?? 0}
            />
            <StatCard
              label="New This Week"
              value={stats?.new_this_week ?? 0}
            />
          </>
        )}
      </div>

      {/* Jobs Over Time */}
      <SectionCard title="Jobs Over Time" loading={loading}>
        <JobsOverTimeChart data={timeData} />
      </SectionCard>

      {/* Top Companies + Top Skills */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionCard title="Top Companies by Postings" loading={loading}>
          <TopCompaniesChart
            data={companies.map((c) => ({
              company: c.company ?? "",
              count: c.count,
            }))}
          />
        </SectionCard>
        <SectionCard title="Top Skills in Demand" loading={loading}>
          <TopSkillsChart
            data={skills.map((s) => ({
              skill: s.skill ?? "",
              count: s.count,
            }))}
          />
        </SectionCard>
      </div>

      {/* Jobs by Location */}
      <SectionCard title="Jobs by Location" loading={loading}>
        <LocationChart
          data={locations.map((l) => ({
            location: l.location ?? "",
            count: l.count,
          }))}
        />
      </SectionCard>

      {/* Breakdowns */}
      <div>
        <h2 className="text-base font-semibold text-slate-200 mb-4">
          Breakdowns
        </h2>
        {loading || !breakdowns ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="bg-slate-800 border border-slate-700 rounded-xl p-4 animate-pulse h-56"
              />
            ))}
          </div>
        ) : (
          <BreakdownCharts
            employmentType={breakdowns.employmentType}
            experienceLevel={breakdowns.experienceLevel}
            sourceSite={breakdowns.sourceSite}
          />
        )}
      </div>

      {/* Footer */}
      <div className="text-center text-xs text-slate-600 py-4">
        Data sourced from IranTalent, Jobinja, and JobVision
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div className="text-slate-400 text-sm">Loading...</div>}>
      <DashboardContent />
    </Suspense>
  );
}
