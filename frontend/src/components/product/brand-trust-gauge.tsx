/** Brand Trust Score gauge — similar to DudScore gauge but for brand-level metrics. */

import type { BrandTrustScore } from "@/types";

interface BrandTrustGaugeProps {
  score: BrandTrustScore;
}

const TIER_COLORS: Record<string, string> = {
  excellent: "#16A34A",
  good: "#65A30D",
  average: "#CA8A04",
  poor: "#EA580C",
  avoid: "#DC2626",
};

const TIER_LABELS: Record<string, string> = {
  excellent: "Excellent",
  good: "Good",
  average: "Average",
  poor: "Poor",
  avoid: "Avoid",
};

export function BrandTrustGauge({ score }: BrandTrustGaugeProps) {
  const cx = 100;
  const cy = 88;
  const r = 72;
  const strokeW = 14;
  const x0 = cx - r;
  const x1 = cx + r;
  const safeScore = score.avgDudScore ?? 0;
  const needleAngle = Math.PI * (1 - safeScore / 100);
  const nx = cx + r * Math.cos(needleAngle);
  const ny = cy - r * Math.sin(needleAngle);
  const innerR = r - strokeW / 2 - 2;
  const innerX = cx + innerR * Math.cos(needleAngle);
  const innerY = cy - innerR * Math.sin(needleAngle);
  const color = TIER_COLORS[score.trustTier] ?? "#6B7280";
  const label = TIER_LABELS[score.trustTier] ?? "N/A";

  const metrics = [
    {
      label: "Products Scored",
      value: score.productCount.toString(),
    },
    {
      label: "Avg Fake Reviews",
      value: score.avgFakeReviewPct != null ? `${score.avgFakeReviewPct.toFixed(1)}%` : "—",
    },
    {
      label: "Price Stability",
      value: score.avgPriceStability != null ? `${Math.round(score.avgPriceStability)}/100` : "—",
    },
    {
      label: "Quality Consistency",
      value:
        score.qualityConsistency != null
          ? `σ ${score.qualityConsistency.toFixed(1)}`
          : "—",
      hint: "Lower = more consistent",
    },
  ];

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
      <h2 className="text-lg font-semibold text-[#1E293B] mb-4">Brand Trust Score</h2>

      {/* Gauge */}
      <div className="flex flex-col items-center mb-6">
        <svg
          viewBox="0 0 200 105"
          className="w-full max-w-[220px]"
          aria-label={`Brand Trust Score ${Math.round(safeScore)}`}
        >
          <defs>
            <linearGradient id="brand-gauge-gradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#DC2626" />
              <stop offset="35%" stopColor="#F59E0B" />
              <stop offset="65%" stopColor="#84CC16" />
              <stop offset="100%" stopColor="#16A34A" />
            </linearGradient>
          </defs>
          <path
            d={`M ${x0},${cy} A ${r},${r} 0 0 1 ${x1},${cy}`}
            fill="none"
            stroke="#E2E8F0"
            strokeWidth={strokeW}
            strokeLinecap="round"
          />
          <path
            d={`M ${x0},${cy} A ${r},${r} 0 0 1 ${x1},${cy}`}
            fill="none"
            stroke="url(#brand-gauge-gradient)"
            strokeWidth={strokeW}
            strokeLinecap="round"
            pathLength="1"
            strokeDasharray="1"
            strokeDashoffset={1 - safeScore / 100}
          />
          <line
            x1={innerX}
            y1={innerY}
            x2={nx}
            y2={ny}
            stroke="#1E293B"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <circle cx={nx} cy={ny} r="5" fill="#1E293B" />
          <text
            x={cx}
            y={cy - 2}
            textAnchor="middle"
            dominantBaseline="auto"
            fontSize="32"
            fontWeight="800"
            fontFamily="Inter, system-ui, sans-serif"
            fill={color}
          >
            {Math.round(safeScore)}
          </text>
          <text
            x={cx}
            y={cy + 16}
            textAnchor="middle"
            dominantBaseline="hanging"
            fontSize="11"
            fontWeight="600"
            fontFamily="Inter, system-ui, sans-serif"
            fill={color}
            letterSpacing="0.08em"
            style={{ textTransform: "uppercase" }}
          >
            {label}
          </text>
        </svg>
      </div>

      {/* Metric Bars */}
      <div className="space-y-3">
        {metrics.map((m) => (
          <div key={m.label} className="flex items-center justify-between text-sm">
            <span className="text-[#64748B]">
              {m.label}
              {"hint" in m && (
                <span className="text-xs text-slate-400 ml-1">({m.hint})</span>
              )}
            </span>
            <span className="font-medium text-[#1E293B]">{m.value}</span>
          </div>
        ))}
      </div>

      <p className="text-xs text-[#64748B] mt-4">
        Last updated: {new Date(score.computedAt).toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
          year: "numeric",
        })}
      </p>
    </div>
  );
}
