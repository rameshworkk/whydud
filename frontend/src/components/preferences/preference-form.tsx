"use client";

import { useState, useCallback } from "react";
import * as SliderPrimitive from "@radix-ui/react-slider";
import {
  Home,
  Heart,
  Shield,
  Zap,
  Wifi,
  DollarSign,
  Settings,
  Thermometer,
  Wind,
  Droplets,
  Volume2,
  Gauge,
  Filter,
  Cpu,
  Sun,
  Moon,
  Clock,
  Ruler,
  Weight,
  Lightbulb,
  Leaf,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils/index";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  PreferenceSchema,
  PreferenceField,
  PreferenceSection,
} from "@/lib/api/types";

// ── Icon mapping ────────────────────────────────────────────────────────────

const ICON_MAP: Record<string, LucideIcon> = {
  home: Home,
  heart: Heart,
  shield: Shield,
  zap: Zap,
  wifi: Wifi,
  dollar: DollarSign,
  settings: Settings,
  thermometer: Thermometer,
  wind: Wind,
  droplets: Droplets,
  volume: Volume2,
  gauge: Gauge,
  filter: Filter,
  cpu: Cpu,
  sun: Sun,
  moon: Moon,
  clock: Clock,
  ruler: Ruler,
  weight: Weight,
  lightbulb: Lightbulb,
  leaf: Leaf,
};

function getSectionIcon(iconName: string): LucideIcon {
  return ICON_MAP[iconName.toLowerCase()] ?? Settings;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function buildInitialValues(
  schema: PreferenceSchema,
  initial?: Record<string, unknown>
): Record<string, unknown> {
  const values: Record<string, unknown> = {};

  for (const section of schema.schema.sections) {
    for (const field of section.fields) {
      // Priority: initial > default > type-appropriate empty
      if (initial && field.key in initial) {
        values[field.key] = initial[field.key];
      } else if (field.defaultValue !== undefined) {
        values[field.key] = field.defaultValue;
      } else {
        switch (field.type) {
          case "number":
          case "currency":
          case "slider":
            values[field.key] = field.min ?? 0;
            break;
          case "range_slider":
            values[field.key] = [field.min ?? 0, field.max ?? 100];
            break;
          case "toggle":
            values[field.key] = false;
            break;
          case "tags":
            values[field.key] = [];
            break;
          case "dropdown":
          case "radio":
            values[field.key] = "";
            break;
          default:
            values[field.key] = "";
        }
      }
    }
  }

  return values;
}

// ── Props ───────────────────────────────────────────────────────────────────

interface PreferenceFormProps {
  schema: PreferenceSchema;
  initialValues?: Record<string, unknown>;
  onSubmit: (values: Record<string, unknown>) => void | Promise<void>;
  submitting?: boolean;
}

// ── Component ───────────────────────────────────────────────────────────────

export function PreferenceForm({
  schema,
  initialValues,
  onSubmit,
  submitting: externalSubmitting,
}: PreferenceFormProps) {
  const [values, setValues] = useState<Record<string, unknown>>(() =>
    buildInitialValues(schema, initialValues)
  );
  const [internalSubmitting, setInternalSubmitting] = useState(false);

  const submitting = externalSubmitting ?? internalSubmitting;

  const updateField = useCallback((key: string, value: unknown) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;

    setInternalSubmitting(true);
    try {
      await onSubmit(values);
    } finally {
      setInternalSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {schema.schema.sections.map((section) => (
        <SectionBlock
          key={section.key}
          section={section}
          values={values}
          onChange={updateField}
        />
      ))}

      {/* ── Save button ───────────────────────────────────────── */}
      <button
        type="submit"
        disabled={submitting}
        className={cn(
          "w-full rounded-lg py-3.5 text-sm font-semibold text-white transition-colors",
          "bg-[#F97316] hover:bg-[#EA580C]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2",
          "disabled:cursor-not-allowed disabled:opacity-60"
        )}
      >
        {submitting ? "Saving…" : "Save Preferences"}
      </button>
    </form>
  );
}

// ── Section ─────────────────────────────────────────────────────────────────

function SectionBlock({
  section,
  values,
  onChange,
}: {
  section: PreferenceSection;
  values: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
}) {
  const Icon = getSectionIcon(section.icon);

  return (
    <section className="rounded-lg border border-[#E2E8F0] bg-white">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-[#E2E8F0] px-5 py-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#FFF7ED]">
          <Icon className="h-5 w-5 text-[#F97316]" />
        </div>
        <h3 className="text-base font-semibold text-[#1E293B]">
          {section.title}
        </h3>
      </div>

      {/* Fields */}
      <div className="space-y-6 p-5">
        {section.fields.map((field) => (
          <FieldRenderer
            key={field.key}
            field={field}
            value={values[field.key]}
            onChange={(v) => onChange(field.key, v)}
          />
        ))}
      </div>
    </section>
  );
}

// ── Field Renderer ──────────────────────────────────────────────────────────

function FieldRenderer({
  field,
  value,
  onChange,
}: {
  field: PreferenceField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  switch (field.type) {
    case "number":
      return <NumberField field={field} value={value} onChange={onChange} />;
    case "currency":
      return <CurrencyField field={field} value={value} onChange={onChange} />;
    case "dropdown":
      return <DropdownField field={field} value={value} onChange={onChange} />;
    case "radio":
      return <RadioField field={field} value={value} onChange={onChange} />;
    case "tags":
      return <TagsField field={field} value={value} onChange={onChange} />;
    case "toggle":
      return <ToggleField field={field} value={value} onChange={onChange} />;
    case "slider":
      return <SliderField field={field} value={value} onChange={onChange} />;
    case "range_slider":
      return (
        <RangeSliderField field={field} value={value} onChange={onChange} />
      );
    default:
      return null;
  }
}

// ── Shared label ────────────────────────────────────────────────────────────

function FieldLabel({
  label,
  unit,
}: {
  label: string;
  unit?: string;
}) {
  return (
    <label className="block text-sm font-medium text-[#1E293B]">
      {label}
      {unit && (
        <span className="ml-1 text-xs font-normal text-[#64748B]">
          ({unit})
        </span>
      )}
    </label>
  );
}

// ── Quick-select buttons ────────────────────────────────────────────────────

function QuickSelectButtons({
  quickSelect,
  currentValue,
  onSelect,
}: {
  quickSelect: Array<{ label: string; value: unknown }>;
  currentValue: unknown;
  onSelect: (value: unknown) => void;
}) {
  return (
    <div className="mt-3">
      <span className="mb-1.5 block text-xs font-medium text-[#64748B]">
        Quick Select
      </span>
      <div className="flex flex-wrap gap-2">
      {quickSelect.map((qs) => {
        const isActive = JSON.stringify(currentValue) === JSON.stringify(qs.value);
        return (
          <button
            key={qs.label}
            type="button"
            onClick={() => onSelect(qs.value)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1",
              isActive
                ? "border-[#F97316] bg-[#FFF7ED] text-[#F97316]"
                : "border-[#E2E8F0] bg-white text-[#64748B] hover:border-[#CBD5E1] hover:text-[#1E293B]"
            )}
          >
            {qs.label}
          </button>
        );
      })}
      </div>
    </div>
  );
}

// ── Number field ────────────────────────────────────────────────────────────

function NumberField({
  field,
  value,
  onChange,
}: {
  field: PreferenceField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const numVal = typeof value === "number" ? value : 0;

  return (
    <div>
      <FieldLabel label={field.label} />
      <div className="relative mt-1.5">
        <input
          type="number"
          value={numVal}
          min={field.min}
          max={field.max}
          onChange={(e) => onChange(e.target.valueAsNumber || 0)}
          className={cn(
            "w-full rounded-lg border border-[#E2E8F0] bg-white py-2.5 text-sm text-[#1E293B]",
            "placeholder:text-[#94A3B8]",
            "focus:border-[#F97316] focus:outline-none focus:ring-2 focus:ring-[#F97316]/20",
            "transition-colors",
            field.unit ? "pl-3 pr-14" : "px-3"
          )}
        />
        {field.unit && (
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-[#94A3B8]">
            {field.unit}
          </span>
        )}
      </div>
      {field.quickSelect && (
        <QuickSelectButtons
          quickSelect={field.quickSelect}
          currentValue={numVal}
          onSelect={onChange}
        />
      )}
    </div>
  );
}

// ── Currency field ──────────────────────────────────────────────────────────

function CurrencyField({
  field,
  value,
  onChange,
}: {
  field: PreferenceField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const numVal = typeof value === "number" ? value : 0;

  return (
    <div>
      <FieldLabel label={field.label} />
      <div className="relative mt-1.5">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-medium text-[#64748B]">
          ₹
        </span>
        <input
          type="number"
          value={numVal}
          min={field.min}
          max={field.max}
          onChange={(e) => onChange(e.target.valueAsNumber || 0)}
          className={cn(
            "w-full rounded-lg border border-[#E2E8F0] bg-white py-2.5 pl-7 pr-3 text-sm text-[#1E293B]",
            "placeholder:text-[#94A3B8]",
            "focus:border-[#F97316] focus:outline-none focus:ring-2 focus:ring-[#F97316]/20",
            "transition-colors"
          )}
        />
      </div>
      {field.quickSelect && (
        <QuickSelectButtons
          quickSelect={field.quickSelect}
          currentValue={numVal}
          onSelect={onChange}
        />
      )}
    </div>
  );
}

// ── Dropdown field ──────────────────────────────────────────────────────────

function DropdownField({
  field,
  value,
  onChange,
}: {
  field: PreferenceField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const strVal = typeof value === "string" ? value : "";

  return (
    <div>
      <FieldLabel label={field.label} />
      <Select value={strVal} onValueChange={(v) => onChange(v)}>
        <SelectTrigger
          className={cn(
            "mt-1.5 w-full rounded-lg border-[#E2E8F0] text-sm text-[#1E293B]",
            "focus:ring-2 focus:ring-[#F97316]/20 focus:ring-offset-0",
            !strVal && "text-[#94A3B8]"
          )}
        >
          <SelectValue placeholder="Select…" />
        </SelectTrigger>
        <SelectContent>
          {field.options?.map((opt) => (
            <SelectItem key={opt} value={opt} className="text-sm">
              {opt}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

// ── Radio field (pill style) ────────────────────────────────────────────────

function RadioField({
  field,
  value,
  onChange,
}: {
  field: PreferenceField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const strVal = typeof value === "string" ? value : "";

  return (
    <div>
      <FieldLabel label={field.label} />
      <div
        className="mt-2 flex flex-wrap gap-2"
        role="radiogroup"
        aria-label={field.label}
      >
        {field.options?.map((opt) => {
          const isSelected = strVal === opt;
          return (
            <button
              key={opt}
              type="button"
              role="radio"
              aria-checked={isSelected}
              onClick={() => onChange(opt)}
              className={cn(
                "rounded-full border px-4 py-2 text-sm font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1",
                isSelected
                  ? "border-[#1E293B] bg-[#F8FAFC] text-[#1E293B]"
                  : "border-[#E2E8F0] bg-white text-[#64748B] hover:border-[#CBD5E1] hover:text-[#1E293B]"
              )}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Tags field (multi-select chips) ─────────────────────────────────────────

function TagsField({
  field,
  value,
  onChange,
}: {
  field: PreferenceField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const selected = Array.isArray(value) ? (value as string[]) : [];

  function toggle(opt: string) {
    if (selected.includes(opt)) {
      onChange(selected.filter((s) => s !== opt));
    } else {
      onChange([...selected, opt]);
    }
  }

  return (
    <div>
      <FieldLabel label={field.label} />
      <div className="mt-2 flex flex-wrap gap-2">
        {field.options?.map((opt) => {
          const isSelected = selected.includes(opt);
          return (
            <button
              key={opt}
              type="button"
              aria-pressed={isSelected}
              onClick={() => toggle(opt)}
              className={cn(
                "rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1",
                isSelected
                  ? "border-[#F97316] bg-[#FFF7ED] text-[#F97316]"
                  : "border-[#E2E8F0] bg-white text-[#64748B] hover:border-[#CBD5E1] hover:text-[#1E293B]"
              )}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Toggle field ────────────────────────────────────────────────────────────

function ToggleField({
  field,
  value,
  onChange,
}: {
  field: PreferenceField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const checked = typeof value === "boolean" ? value : false;

  return (
    <div className="flex items-center justify-between gap-4">
      <FieldLabel label={field.label} />
      <Switch
        checked={checked}
        onCheckedChange={(v) => onChange(v)}
        className="data-[state=checked]:bg-[#F97316]"
      />
    </div>
  );
}

// ── Slider field (single thumb) ─────────────────────────────────────────────

function SliderField({
  field,
  value,
  onChange,
}: {
  field: PreferenceField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const numVal = typeof value === "number" ? value : (field.min ?? 0);
  const min = field.min ?? 0;
  const max = field.max ?? 100;

  return (
    <div>
      <div className="flex items-center justify-between">
        <FieldLabel label={field.label} unit={field.unit} />
        <span className="text-sm font-semibold text-[#F97316]">
          {numVal}
          {field.unit ? ` ${field.unit}` : ""}
        </span>
      </div>
      <Slider
        value={[numVal]}
        min={min}
        max={max}
        step={1}
        onValueChange={([v]) => onChange(v)}
        className={cn(
          "mt-3",
          "[&_[role=slider]]:border-[#F97316]",
          "[&_[role=slider]]:focus-visible:ring-[#F97316]",
          "[&>span:first-child>span]:bg-[#F97316]"
        )}
      />
      <div className="mt-1 flex justify-between text-xs text-[#94A3B8]">
        <span>{min}{field.unit ? ` ${field.unit}` : ""}</span>
        <span>{max}{field.unit ? ` ${field.unit}` : ""}</span>
      </div>
      {field.quickSelect && (
        <QuickSelectButtons
          quickSelect={field.quickSelect}
          currentValue={numVal}
          onSelect={onChange}
        />
      )}
    </div>
  );
}

// ── Range slider field (dual thumb) ─────────────────────────────────────────

function RangeSliderField({
  field,
  value,
  onChange,
}: {
  field: PreferenceField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const rangeVal = Array.isArray(value) ? (value as number[]) : [field.min ?? 0, field.max ?? 100];
  const min = field.min ?? 0;
  const max = field.max ?? 100;
  const low = rangeVal[0] ?? min;
  const high = rangeVal[1] ?? max;

  return (
    <div>
      <div className="flex items-center justify-between">
        <FieldLabel label={field.label} unit={field.unit} />
        <span className="text-sm font-semibold text-[#F97316]">
          {low} – {high}
          {field.unit ? ` ${field.unit}` : ""}
        </span>
      </div>
      <SliderPrimitive.Root
        value={[low, high]}
        min={min}
        max={max}
        step={1}
        onValueChange={(v) => onChange(v)}
        className="relative mt-3 flex w-full touch-none select-none items-center"
      >
        <SliderPrimitive.Track className="relative h-2 w-full grow overflow-hidden rounded-full bg-[#F1F5F9]">
          <SliderPrimitive.Range className="absolute h-full bg-[#F97316]" />
        </SliderPrimitive.Track>
        <SliderPrimitive.Thumb
          className={cn(
            "block h-5 w-5 rounded-full border-2 border-[#F97316] bg-white",
            "ring-offset-white transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2"
          )}
        />
        <SliderPrimitive.Thumb
          className={cn(
            "block h-5 w-5 rounded-full border-2 border-[#F97316] bg-white",
            "ring-offset-white transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2"
          )}
        />
      </SliderPrimitive.Root>
      <div className="mt-1 flex justify-between text-xs text-[#94A3B8]">
        <span>{min}{field.unit ? ` ${field.unit}` : ""}</span>
        <span>{max}{field.unit ? ` ${field.unit}` : ""}</span>
      </div>
      {field.quickSelect && (
        <QuickSelectButtons
          quickSelect={field.quickSelect}
          currentValue={rangeVal}
          onSelect={onChange}
        />
      )}
    </div>
  );
}
