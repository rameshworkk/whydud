/** DudScore component breakdown — 5 colored dots + label + value per row. */

interface ScoreComponent {
  label: string;
  value: number; // 0–100
  color: string; // unused currently, kept for future theming
}

interface CategoryScoreBarsProps {
  components: ScoreComponent[];
}

function getDotColor(value: number): string {
  if (value >= 80) return "bg-green-500";
  if (value >= 60) return "bg-lime-400";
  if (value >= 40) return "bg-yellow-400";
  if (value >= 20) return "bg-orange-400";
  return "bg-red-500";
}

export function CategoryScoreBars({ components }: CategoryScoreBarsProps) {
  return (
    <div className="flex flex-col gap-2.5">
      {components.map((c) => {
        const filledDots = Math.round((c.value / 100) * 5);
        const dotColor = getDotColor(c.value);

        return (
          <div key={c.label} className="flex items-center gap-3">
            {/* Dots */}
            <div className="flex gap-1 shrink-0">
              {Array.from({ length: 5 }, (_, i) => (
                <span
                  key={i}
                  className={`inline-block w-2.5 h-2.5 rounded-full ${
                    i < filledDots ? dotColor : "bg-slate-200"
                  }`}
                />
              ))}
            </div>

            {/* Label */}
            <span className="text-xs text-slate-600 flex-1 min-w-0">{c.label}</span>

            {/* Value */}
            <span className="text-xs font-semibold text-slate-700 shrink-0">{c.value}</span>
          </div>
        );
      })}
    </div>
  );
}
