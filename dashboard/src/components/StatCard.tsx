interface StatCardProps {
  label: string;
  value: number | string;
  description?: string;
}

export default function StatCard({ label, value, description }: StatCardProps) {
  const formatted =
    typeof value === "number" ? value.toLocaleString() : value;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
      <p className="text-sm text-slate-400 mb-1">{label}</p>
      <p className="text-3xl font-bold text-slate-100">{formatted}</p>
      {description && (
        <p className="text-xs text-slate-500 mt-1">{description}</p>
      )}
    </div>
  );
}
