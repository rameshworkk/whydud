"use client";

import { useRef } from "react";
import { Upload, Lightbulb, ChevronRight, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils/index";
import { MARKETPLACES } from "@/config/marketplace";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface VerifyPurchaseData {
  hasPurchaseProof: boolean | null;
  invoiceFile: File | null;
  platform: string;
  sellerName: string;
  deliveryDate: string;
  pricePaid: string;
}

interface VerifyPurchaseTabProps {
  data: VerifyPurchaseData;
  onChange: (update: Partial<VerifyPurchaseData>) => void;
  onNext: () => void;
  onSkip: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function VerifyPurchaseTab({
  data,
  onChange,
  onNext,
  onSkip,
}: VerifyPurchaseTabProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    onChange({ invoiceFile: file });
    // Reset input so re-selecting the same file triggers change
    e.target.value = "";
  }

  return (
    <div className="space-y-6">
      {/* ── Proof of purchase question ──────────────────────────── */}
      <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          {/* Left: question + radios */}
          <div className="space-y-3">
            <p className="text-base font-semibold text-[#1E293B]">
              Do you have a proof of purchase?
            </p>

            <div className="flex items-center gap-5">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="purchase-proof"
                  checked={data.hasPurchaseProof === true}
                  onChange={() => onChange({ hasPurchaseProof: true })}
                  className="h-4 w-4 border-[#E2E8F0] text-[#1E293B] accent-[#1E293B] focus:ring-[#F97316]"
                />
                <span className="text-sm text-[#1E293B]">Yes</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="purchase-proof"
                  checked={data.hasPurchaseProof === false}
                  onChange={() =>
                    onChange({ hasPurchaseProof: false, invoiceFile: null })
                  }
                  className="h-4 w-4 border-[#E2E8F0] text-[#1E293B] accent-[#1E293B] focus:ring-[#F97316]"
                />
                <span className="text-sm text-[#1E293B]">No</span>
              </label>
            </div>

            {/* Upload invoice button (shown when Yes) */}
            {data.hasPurchaseProof === true && (
              <div className="mt-1">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,.pdf"
                  onChange={handleFileChange}
                  className="hidden"
                  aria-label="Upload invoice"
                />

                {data.invoiceFile ? (
                  <div className="flex items-center gap-2 rounded-lg border border-[#E2E8F0] bg-white px-4 py-2.5">
                    <FileText className="h-4 w-4 text-[#64748B] shrink-0" />
                    <span className="flex-1 min-w-0 truncate text-sm text-[#1E293B]">
                      {data.invoiceFile.name}
                    </span>
                    <button
                      type="button"
                      onClick={() => onChange({ invoiceFile: null })}
                      className="shrink-0 rounded p-0.5 text-[#64748B] hover:text-red-500 hover:bg-red-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]"
                      aria-label="Remove file"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className={cn(
                      "flex w-full max-w-xs items-center justify-center gap-2 rounded-lg px-6 py-3",
                      "bg-[#F1F5F9] text-sm font-medium text-[#1E293B]",
                      "hover:bg-[#E2E8F0] active:bg-[#CBD5E1]",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316]",
                      "transition-colors"
                    )}
                  >
                    <Upload className="h-4 w-4" />
                    Upload invoice
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Right: credibility badge callout */}
          <div className="flex items-center gap-2.5 rounded-lg border border-[#E2E8F0] bg-white px-4 py-3 sm:max-w-xs">
            <Lightbulb className="h-5 w-5 shrink-0 text-[#64748B]" />
            <p className="text-sm text-[#1E293B]">
              Earn a credibility badge by uploading an invoice.
            </p>
          </div>
        </div>
      </div>

      {/* ── Purchase details form ──────────────────────────────── */}
      <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-6">
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          {/* Platform Purchased From */}
          <div className="space-y-1.5">
            <label
              htmlFor="vp-platform"
              className="block text-sm font-semibold text-[#1E293B]"
            >
              Platform Purchased From
            </label>
            <div className="relative">
              <select
                id="vp-platform"
                value={data.platform}
                onChange={(e) => onChange({ platform: e.target.value })}
                className={cn(
                  "h-10 w-full appearance-none rounded-lg border border-[#E2E8F0] bg-white px-3 pr-9 text-sm",
                  "text-[#1E293B] placeholder:text-[#94A3B8]",
                  "focus:border-[#F97316] focus:outline-none focus:ring-2 focus:ring-[#F97316]/20",
                  "transition-colors",
                  !data.platform && "text-[#94A3B8]"
                )}
              >
                <option value="">Select platform</option>
                {MARKETPLACES.map((m) => (
                  <option key={m.slug} value={m.slug}>
                    {m.name}
                  </option>
                ))}
                <option value="offline">Offline Store</option>
                <option value="other">Other</option>
              </select>
              <ChevronRight className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 rotate-90 text-[#64748B]" />
            </div>
          </div>

          {/* Delivery Date */}
          <div className="space-y-1.5">
            <label
              htmlFor="vp-delivery-date"
              className="block text-sm font-semibold text-[#1E293B]"
            >
              Delivery Date
            </label>
            <input
              id="vp-delivery-date"
              type="date"
              value={data.deliveryDate}
              onChange={(e) => onChange({ deliveryDate: e.target.value })}
              placeholder="dd-mm-yy"
              className={cn(
                "h-10 w-full rounded-lg border border-[#E2E8F0] bg-white px-3 text-sm",
                "text-[#1E293B] placeholder:text-[#94A3B8]",
                "focus:border-[#F97316] focus:outline-none focus:ring-2 focus:ring-[#F97316]/20",
                "transition-colors"
              )}
            />
          </div>

          {/* Seller Name */}
          <div className="space-y-1.5">
            <label
              htmlFor="vp-seller"
              className="block text-sm font-semibold text-[#1E293B]"
            >
              Seller Name
            </label>
            <input
              id="vp-seller"
              type="text"
              value={data.sellerName}
              onChange={(e) => onChange({ sellerName: e.target.value })}
              placeholder="Enter seller name"
              className={cn(
                "h-10 w-full rounded-lg border border-[#E2E8F0] bg-white px-3 text-sm",
                "text-[#1E293B] placeholder:text-[#94A3B8]",
                "focus:border-[#F97316] focus:outline-none focus:ring-2 focus:ring-[#F97316]/20",
                "transition-colors"
              )}
            />
          </div>

          {/* Price Paid */}
          <div className="space-y-1.5">
            <label
              htmlFor="vp-price"
              className="block text-sm font-semibold text-[#1E293B]"
            >
              Price Paid
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[#64748B]">
                ₹
              </span>
              <input
                id="vp-price"
                type="text"
                inputMode="numeric"
                value={data.pricePaid}
                onChange={(e) => {
                  const v = e.target.value.replace(/[^\d]/g, "");
                  onChange({ pricePaid: v });
                }}
                placeholder="2000"
                className={cn(
                  "h-10 w-full rounded-lg border border-[#E2E8F0] bg-white pl-7 pr-3 text-sm",
                  "text-[#1E293B] placeholder:text-[#94A3B8]",
                  "focus:border-[#F97316] focus:outline-none focus:ring-2 focus:ring-[#F97316]/20",
                  "transition-colors"
                )}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── Footer buttons ─────────────────────────────────────── */}
      <div className="flex items-center justify-end gap-4 pt-2">
        <button
          type="button"
          onClick={onSkip}
          className={cn(
            "px-5 py-2.5 text-sm font-medium text-[#1E293B]",
            "hover:text-[#64748B]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] rounded-lg",
            "transition-colors"
          )}
        >
          Skip
        </button>
        <button
          type="button"
          onClick={onNext}
          className={cn(
            "rounded-lg px-8 py-2.5 text-sm font-medium",
            "bg-[#E2E8F0] text-[#1E293B]",
            "hover:bg-[#CBD5E1] active:bg-[#94A3B8]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1",
            "transition-colors"
          )}
        >
          Next
        </button>
      </div>
    </div>
  );
}
