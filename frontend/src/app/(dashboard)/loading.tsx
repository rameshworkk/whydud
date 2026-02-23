export default function DashboardLoading() {
  return (
    <div className="flex flex-col gap-6 animate-pulse">
      <div className="h-7 w-48 rounded bg-slate-200" />
      <div className="h-4 w-64 rounded bg-slate-100" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="rounded-xl border border-slate-200 bg-white p-4 h-24" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 h-64" />
        <div className="rounded-xl border border-slate-200 bg-white p-4 h-64" />
      </div>
    </div>
  );
}
