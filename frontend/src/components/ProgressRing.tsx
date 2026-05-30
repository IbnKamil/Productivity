export function ProgressRing({ value }: { value: number }) {
  const normalized = Math.max(0, Math.min(100, value));
  return (
    <div className="relative grid h-24 w-24 place-items-center rounded-full bg-slate-900/80">
      <svg className="absolute h-24 w-24 -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="42" fill="none" stroke="#1e293b" strokeWidth="9" />
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke="#34d399"
          strokeLinecap="round"
          strokeWidth="9"
          strokeDasharray={`${normalized * 2.64} 264`}
        />
      </svg>
      <span className="text-lg font-bold text-white">{normalized}%</span>
    </div>
  );
}
