/** Semi-circular DudScore gauge with gradient arc and needle indicator. */

interface DudScoreGaugeProps {
  score: number | null;
  label?: string;
}

export function DudScoreGauge({ score, label }: DudScoreGaugeProps) {
  const cx = 100;
  const cy = 88;
  const r = 72;
  const strokeW = 14;

  // Start: (cx-r, cy) = left end. Arc goes clockwise through top to (cx+r, cy).
  const x0 = cx - r;
  const x1 = cx + r;

  // Needle position at score S: angle from positive x-axis = π*(1 - S/100)
  const safeScore = score ?? 0;
  const needleAngle = Math.PI * (1 - safeScore / 100);
  const nx = cx + r * Math.cos(needleAngle);
  const ny = cy - r * Math.sin(needleAngle);

  // Inner needle line from center
  const innerR = r - strokeW / 2 - 2;
  const innerX = cx + innerR * Math.cos(needleAngle);
  const innerY = cy - innerR * Math.sin(needleAngle);

  const scoreLabel =
    label ??
    (score == null
      ? "Not Rated"
      : score >= 90
      ? "Excellent"
      : score >= 70
      ? "Good"
      : score >= 50
      ? "Average"
      : score >= 30
      ? "Below Average"
      : "Dud");

  const scoreColor =
    score == null
      ? "#6B7280"
      : score >= 90
      ? "#16A34A"
      : score >= 70
      ? "#65A30D"
      : score >= 50
      ? "#CA8A04"
      : score >= 30
      ? "#EA580C"
      : "#DC2626";

  return (
    <div className="flex flex-col items-center w-full">
      <svg
        viewBox="0 0 200 105"
        className="w-full max-w-[220px]"
        aria-label={`DudScore ${score ?? "not rated"}`}
      >
        <defs>
          {/* Gradient: red → orange → yellow → green (left to right) */}
          <linearGradient id="gauge-gradient" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#DC2626" />
            <stop offset="35%" stopColor="#F59E0B" />
            <stop offset="65%" stopColor="#84CC16" />
            <stop offset="100%" stopColor="#16A34A" />
          </linearGradient>
          {/* Clip path for the colored arc region only */}
          <clipPath id="gauge-clip">
            <rect x="0" y="0" width="200" height="105" />
          </clipPath>
        </defs>

        {/* Background track */}
        <path
          d={`M ${x0},${cy} A ${r},${r} 0 0 1 ${x1},${cy}`}
          fill="none"
          stroke="#E2E8F0"
          strokeWidth={strokeW}
          strokeLinecap="round"
        />

        {/* Colored arc fill up to score */}
        {score != null && (
          <path
            d={`M ${x0},${cy} A ${r},${r} 0 0 1 ${x1},${cy}`}
            fill="none"
            stroke="url(#gauge-gradient)"
            strokeWidth={strokeW}
            strokeLinecap="round"
            pathLength="1"
            strokeDasharray="1"
            strokeDashoffset={1 - safeScore / 100}
          />
        )}

        {/* Needle line from inner edge to arc edge */}
        {score != null && (
          <line
            x1={innerX}
            y1={innerY}
            x2={nx}
            y2={ny}
            stroke="#1E293B"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        )}

        {/* Needle dot at arc position */}
        {score != null && (
          <circle cx={nx} cy={ny} r="5" fill="#1E293B" />
        )}

        {/* Score number */}
        <text
          x={cx}
          y={cy - 2}
          textAnchor="middle"
          dominantBaseline="auto"
          fontSize="32"
          fontWeight="800"
          fontFamily="Inter, system-ui, sans-serif"
          fill={scoreColor}
        >
          {score != null ? Math.round(score) : "—"}
        </text>

        {/* Score label */}
        <text
          x={cx}
          y={cy + 16}
          textAnchor="middle"
          dominantBaseline="hanging"
          fontSize="11"
          fontWeight="600"
          fontFamily="Inter, system-ui, sans-serif"
          fill={scoreColor}
          letterSpacing="0.08em"
          style={{ textTransform: "uppercase" }}
        >
          {scoreLabel}
        </text>
      </svg>
    </div>
  );
}
