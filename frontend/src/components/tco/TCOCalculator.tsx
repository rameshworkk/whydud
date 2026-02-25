"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { tcoApi } from "@/lib/api/tco";
import type { TCOCalculatePayload } from "@/lib/api/tco";
import { formatPrice } from "@/lib/utils/format";
import { cn } from "@/lib/utils/index";
import type { TCOModelSchema, TCOResult, TCOInput } from "@/lib/api/types";

/* ── Chart colours — Whydud palette ─────────────────────────────────────── */
const COLORS = {
  purchase: "#F97316",
  ongoing: "#4DB6AC",
  resale: "#16A34A",
};

/* ── Props ──────────────────────────────────────────────────────────────── */
interface TCOCalculatorProps {
  categorySlug: string;
  products?: Array<{ slug: string; title: string }>;
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */
function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function formatAxisValue(paisa: number): string {
  const rupees = paisa / 100;
  if (rupees >= 100000) return `\u20B9${(rupees / 100000).toFixed(1)}L`;
  if (rupees >= 1000) return `\u20B9${Math.round(rupees / 1000)}k`;
  return `\u20B9${Math.round(rupees)}`;
}

/* ── Dynamic Input ──────────────────────────────────────────────────────── */
function DynamicInput({
  field,
  value,
  onChange,
}: {
  field: TCOInput;
  value: number;
  onChange: (v: number) => void;
}) {
  const isCurrency = field.type === "currency";
  const step = field.type === "decimal" ? 0.01 : 1;

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-[#1E293B]">
        {field.label}
        {field.unit && (
          <span className="ml-1 text-[#94A3B8] font-normal">
            ({field.unit})
          </span>
        )}
      </label>
      <div className="relative">
        {isCurrency && (
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-[#64748B]">
            {"\u20B9"}
          </span>
        )}
        <input
          type="number"
          step={step}
          min={field.min}
          max={field.max}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className={cn(
            "w-full rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-sm text-[#1E293B]",
            "focus:border-[#F97316] focus:outline-none focus:ring-1 focus:ring-[#F97316]/20",
            "transition-colors",
            isCurrency && "pl-7"
          )}
        />
      </div>
    </div>
  );
}

/* ── Summary Card ───────────────────────────────────────────────────────── */
function SummaryCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border p-4 text-center",
        highlight
          ? "border-[#F97316] bg-[#FFF7ED]"
          : "border-[#E2E8F0] bg-white"
      )}
    >
      <p className="text-[10px] uppercase tracking-wide text-[#94A3B8] mb-1">
        {label}
      </p>
      <p
        className={cn(
          "text-lg font-bold",
          highlight ? "text-[#F97316]" : "text-[#1E293B]"
        )}
      >
        {formatPrice(Math.round(value))}
      </p>
    </div>
  );
}

/* ── Skeleton ───────────────────────────────────────────────────────────── */
function TCOSkeleton() {
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-6 animate-pulse">
      <div className="h-5 w-48 bg-slate-200 rounded mb-2" />
      <div className="h-3.5 w-64 bg-slate-200 rounded mb-6" />
      <div className="flex gap-2 mb-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-8 w-24 bg-slate-200 rounded-lg" />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i}>
            <div className="h-3 w-24 bg-slate-200 rounded mb-2" />
            <div className="h-9 bg-slate-200 rounded-lg" />
          </div>
        ))}
      </div>
      <div className="h-6 w-full bg-slate-200 rounded mb-6" />
      <div className="grid grid-cols-3 gap-3 mb-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-20 bg-slate-200 rounded-lg" />
        ))}
      </div>
      <div className="h-56 bg-slate-200 rounded-lg" />
    </div>
  );
}

/* ── Custom Tooltip ──────────────────────────────────────────────────────── */
function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;

  const total = payload.reduce((sum, entry) => sum + entry.value, 0);

  return (
    <div className="rounded-lg border border-[#E2E8F0] bg-white p-3 shadow-md">
      <p className="text-xs font-semibold text-[#1E293B] mb-2">{label}</p>
      {payload.map((entry) => (
        <div
          key={entry.name}
          className="flex items-center justify-between gap-6 text-xs mb-0.5"
        >
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-[#64748B]">{entry.name}</span>
          </span>
          <span className="font-semibold text-[#1E293B]">
            {formatPrice(Math.round(entry.value))}
          </span>
        </div>
      ))}
      <div className="mt-1.5 pt-1.5 border-t border-[#E2E8F0] flex justify-between text-xs">
        <span className="font-medium text-[#64748B]">Total</span>
        <span className="font-bold text-[#1E293B]">
          {formatPrice(Math.round(total))}
        </span>
      </div>
    </div>
  );
}

/* ── Main Component ──────────────────────────────────────────────────────── */
export function TCOCalculator({
  categorySlug,
  products = [],
}: TCOCalculatorProps) {
  const [model, setModel] = useState<TCOModelSchema | null>(null);
  const [inputs, setInputs] = useState<Record<string, number>>({});
  const [ownershipYears, setOwnershipYears] = useState(5);
  const [results, setResults] = useState<TCOResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activePreset, setActivePreset] = useState<string>("default");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  /* ── Fetch model on mount ─────────────────────────────────────────────── */
  useEffect(() => {
    let cancelled = false;

    async function fetchModel() {
      try {
        const res = await tcoApi.getModel(categorySlug);
        if (cancelled) return;
        if (res.success && "data" in res) {
          const data = res.data as TCOModelSchema;
          setModel(data);

          // Set defaults from input schema
          const defaults: Record<string, number> = {};
          for (const field of data.inputSchema?.inputs ?? []) {
            if (field.defaultValue != null) {
              defaults[field.key] = Number(field.defaultValue);
            }
          }
          setInputs(defaults);
          setOwnershipYears(
            data.inputSchema?.ownershipYears?.default ?? 5
          );
        } else {
          setError("TCO model not available for this category.");
        }
      } catch {
        if (!cancelled) setError("Failed to load TCO model.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchModel();
    return () => {
      cancelled = true;
    };
  }, [categorySlug]);

  /* ── Calculate TCO for each product ───────────────────────────────────── */
  const calculate = useCallback(async () => {
    if (!model || products.length === 0) return;
    setCalculating(true);

    try {
      const promises = products.map((p) => {
        const payload: TCOCalculatePayload = {
          productSlug: p.slug,
          ownershipYears,
          inputs,
        };
        return tcoApi.calculateTCO(payload);
      });

      const responses = await Promise.all(promises);
      const newResults: TCOResult[] = [];

      for (const res of responses) {
        if (res.success && "data" in res) {
          newResults.push(res.data as TCOResult);
        }
      }

      setResults(newResults);
    } catch {
      // Keep previous results on error
    } finally {
      setCalculating(false);
    }
  }, [model, products, inputs, ownershipYears]);

  /* ── Debounced recalculation ──────────────────────────────────────────── */
  useEffect(() => {
    if (!model || products.length === 0) return;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(calculate, 500);
    return () => clearTimeout(debounceRef.current);
  }, [model, inputs, ownershipYears, calculate]);

  /* ── Input handlers ───────────────────────────────────────────────────── */
  function handleInputChange(key: string, value: number) {
    setActivePreset("");
    setInputs((prev) => ({ ...prev, [key]: value }));
  }

  function handleOwnershipChange(value: number) {
    setOwnershipYears(value);
  }

  function applyPreset(presetKey: string) {
    if (!model) return;
    const presetValues = model.inputSchema?.presets?.[presetKey];
    if (!presetValues) return;

    const newInputs: Record<string, number> = {};
    for (const field of model.inputSchema?.inputs ?? []) {
      const presetVal = presetValues[field.key];
      if (presetVal != null) {
        newInputs[field.key] = Number(presetVal);
      } else if (field.defaultValue != null) {
        newInputs[field.key] = Number(field.defaultValue);
      }
    }
    setInputs(newInputs);
    setActivePreset(presetKey);
  }

  /* ── Build chart data ─────────────────────────────────────────────────── */
  const chartData = results.map((r, i) => {
    const years = r.ownershipYears || ownershipYears;
    const productTitle = products[i]?.title ?? `Product ${i + 1}`;
    const name =
      productTitle.length > 25
        ? productTitle.slice(0, 23) + "\u2026"
        : productTitle;

    return {
      name,
      purchase: r.breakdown.purchase.total,
      ongoing: r.breakdown.ongoingAnnual.total * years,
      resale: Math.abs(r.breakdown.resale.total),
    };
  });

  /* ── Render ───────────────────────────────────────────────────────────── */
  if (loading) return <TCOSkeleton />;

  if (error) {
    return (
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-6">
        <h3 className="text-lg font-bold text-[#1E293B] mb-1">
          Total Cost of Ownership
        </h3>
        <p className="text-sm text-[#64748B]">{error}</p>
      </div>
    );
  }

  if (!model) return null;

  const yearsConfig = model.inputSchema?.ownershipYears ?? {
    min: 1,
    max: 10,
    default: 5,
  };
  const presets = model.inputSchema?.presets ?? {};
  const presetKeys = Object.keys(presets);
  const inputFields = model.inputSchema?.inputs ?? [];
  const firstResult = results[0] ?? null;

  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-6">
      <h3 className="text-lg font-bold text-[#1E293B] mb-1">
        Total Cost of Ownership
      </h3>
      <p className="text-sm text-[#64748B] mb-6">
        How much will this really cost over {ownershipYears}{" "}
        {ownershipYears === 1 ? "year" : "years"}?
      </p>

      {/* ── Preset buttons ──────────────────────────────────────────── */}
      {presetKeys.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {presetKeys.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => applyPreset(key)}
              className={cn(
                "rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2",
                activePreset === key
                  ? "bg-[#F97316] text-white"
                  : "border border-[#E2E8F0] text-[#64748B] hover:border-[#F97316] hover:text-[#F97316]"
              )}
            >
              {capitalize(key)}
            </button>
          ))}
        </div>
      )}

      {/* ── Dynamic input fields ────────────────────────────────────── */}
      {inputFields.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          {inputFields.map((field) => (
            <DynamicInput
              key={field.key}
              field={field}
              value={inputs[field.key] ?? 0}
              onChange={(v) => handleInputChange(field.key, v)}
            />
          ))}
        </div>
      )}

      {/* ── Ownership years slider ──────────────────────────────────── */}
      <div className="mb-6">
        <label className="flex items-center justify-between text-sm font-medium text-[#1E293B] mb-2">
          <span>Ownership period</span>
          <span className="text-[#F97316] font-bold">
            {ownershipYears} {ownershipYears === 1 ? "year" : "years"}
          </span>
        </label>
        <input
          type="range"
          min={yearsConfig.min}
          max={yearsConfig.max}
          value={ownershipYears}
          onChange={(e) => handleOwnershipChange(Number(e.target.value))}
          className="w-full accent-[#F97316] h-1.5 cursor-pointer"
        />
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-[#94A3B8]">
            {yearsConfig.min} yr
          </span>
          <span className="text-[10px] text-[#94A3B8]">
            {yearsConfig.max} yrs
          </span>
        </div>
      </div>

      {/* ── Results ─────────────────────────────────────────────────── */}
      {calculating && results.length === 0 ? (
        <div className="h-64 flex items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#F97316] border-t-transparent" />
        </div>
      ) : firstResult ? (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-3 gap-3 mb-6">
            <SummaryCard
              label="Total Cost"
              value={firstResult.total}
              highlight
            />
            <SummaryCard label="Per Year" value={firstResult.perYear} />
            <SummaryCard label="Per Month" value={firstResult.perMonth} />
          </div>

          {/* Stacked bar chart */}
          <div
            className={cn(
              "relative",
              calculating && "opacity-50 transition-opacity"
            )}
          >
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#E2E8F0"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11, fill: "#64748B" }}
                    axisLine={{ stroke: "#E2E8F0" }}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={formatAxisValue}
                    tick={{ fontSize: 11, fill: "#94A3B8" }}
                    axisLine={false}
                    tickLine={false}
                    width={56}
                  />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend
                    iconType="square"
                    iconSize={10}
                    wrapperStyle={{ fontSize: 11 }}
                  />
                  <Bar
                    dataKey="purchase"
                    stackId="cost"
                    fill={COLORS.purchase}
                    name="Purchase"
                  />
                  <Bar
                    dataKey="ongoing"
                    stackId="cost"
                    fill={COLORS.ongoing}
                    name="Ongoing"
                  />
                  <Bar
                    dataKey="resale"
                    stackId="cost"
                    fill={COLORS.resale}
                    name="Resale Value"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Breakdown detail for single product */}
          {results.length === 1 && firstResult.breakdown && (
            <div className="mt-6 pt-5 border-t border-[#E2E8F0]">
              <p className="text-xs font-semibold text-[#1E293B] mb-3">
                Cost Breakdown
              </p>
              <div className="flex flex-col gap-2">
                {(
                  [
                    ["purchase", COLORS.purchase],
                    ["ongoingAnnual", COLORS.ongoing],
                    ["oneTimeRisk", "#64748B"],
                    ["resale", COLORS.resale],
                  ] as const
                ).map(([groupKey, color]) => {
                  const group =
                    firstResult.breakdown[groupKey];
                  if (!group || group.total === 0) return null;

                  const isAnnual = groupKey === "ongoingAnnual";
                  const displayTotal = isAnnual
                    ? group.total * (firstResult.ownershipYears || ownershipYears)
                    : group.total;

                  return (
                    <div
                      key={groupKey}
                      className="flex items-center justify-between text-xs"
                    >
                      <span className="flex items-center gap-2">
                        <span
                          className="inline-block h-2 w-2 rounded-sm"
                          style={{ backgroundColor: color }}
                        />
                        <span className="text-[#64748B]">
                          {group.label}
                          {isAnnual && (
                            <span className="text-[#94A3B8]">
                              {" "}
                              ({formatPrice(Math.round(group.total))}/yr
                              {" \u00D7 "}
                              {firstResult.ownershipYears || ownershipYears}
                              )
                            </span>
                          )}
                        </span>
                      </span>
                      <span className="font-semibold text-[#1E293B]">
                        {formatPrice(Math.round(displayTotal))}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      ) : products.length === 0 ? (
        <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-8 text-center">
          <p className="text-sm text-[#64748B]">
            Select a product to calculate Total Cost of Ownership.
          </p>
        </div>
      ) : null}
    </div>
  );
}
