"use client";

import { useState, useEffect, useCallback } from "react";
import { Bell, BellRing, Pencil, Trash2, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils/index";
import { formatPrice } from "@/lib/utils/format";
import { alertsApi } from "@/lib/api/alerts";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { PriceAlert } from "@/types/product";

// ── Props ───────────────────────────────────────────────────────────────────

interface Marketplace {
  slug: string;
  name: string;
}

interface PriceAlertButtonProps {
  productId: string;
  currentPrice: number; // paisa
  marketplaces: Marketplace[];
}

// ── Component ───────────────────────────────────────────────────────────────

export function PriceAlertButton({
  productId,
  currentPrice,
  marketplaces,
}: PriceAlertButtonProps) {
  const [open, setOpen] = useState(false);
  const [existingAlert, setExistingAlert] = useState<PriceAlert | null>(null);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);

  // Form state
  const [targetPrice, setTargetPrice] = useState("");
  const [marketplace, setMarketplace] = useState("any");
  const [editing, setEditing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Check for existing alert on mount ────────────────────────────────

  const checkExisting = useCallback(async () => {
    setChecking(true);
    try {
      const res = await alertsApi.getAlerts();
      if (res.success) {
        const match = res.data.find(
          (a) => a.product === productId && a.isActive
        );
        setExistingAlert(match ?? null);
      }
    } catch {
      // silently fail — user will see "Set" mode
    } finally {
      setChecking(false);
    }
  }, [productId]);

  useEffect(() => {
    checkExisting();
  }, [checkExisting]);

  // ── Open dialog ──────────────────────────────────────────────────────

  function handleOpen() {
    setError(null);
    if (existingAlert) {
      // Pre-fill with existing alert values
      setTargetPrice(String(existingAlert.targetPrice / 100));
      setMarketplace(existingAlert.marketplace ?? "any");
      setEditing(false);
    } else {
      // Suggest 10% below current price
      const suggested = Math.floor((currentPrice * 0.9) / 100);
      setTargetPrice(String(suggested));
      setMarketplace("any");
      setEditing(false);
    }
    setOpen(true);
  }

  // ── Create / Update alert ────────────────────────────────────────────

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const pricePaisa = Math.round(Number(targetPrice) * 100);

    if (!targetPrice || isNaN(pricePaisa) || pricePaisa <= 0) {
      setError("Enter a valid target price");
      return;
    }
    if (pricePaisa >= currentPrice) {
      setError("Target price should be lower than the current price");
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      const mkt = marketplace === "any" ? undefined : marketplace;

      if (existingAlert && editing) {
        const res = await alertsApi.updateAlert(existingAlert.id, pricePaisa);
        if (res.success) {
          setExistingAlert(res.data);
          setEditing(false);
        } else {
          setError("Failed to update alert. Please try again.");
        }
      } else {
        const res = await alertsApi.createPriceAlert(
          productId,
          pricePaisa,
          mkt
        );
        if (res.success) {
          setExistingAlert(res.data);
        } else {
          setError("Failed to create alert. Please try again.");
        }
      }
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  // ── Delete alert ─────────────────────────────────────────────────────

  async function handleDelete() {
    if (!existingAlert) return;

    setDeleting(true);
    setError(null);

    try {
      const res = await alertsApi.deleteAlert(existingAlert.id);
      if (res.success) {
        setExistingAlert(null);
        setOpen(false);
      } else {
        setError("Failed to delete alert. Please try again.");
      }
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setDeleting(false);
    }
  }

  // ── Render ───────────────────────────────────────────────────────────

  const hasAlert = !!existingAlert;

  return (
    <>
      {/* ── Trigger button ──────────────────────────────────── */}
      <button
        type="button"
        onClick={handleOpen}
        disabled={checking}
        className={cn(
          "inline-flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1",
          hasAlert
            ? "border-[#F97316] bg-[#FFF7ED] text-[#F97316] hover:bg-[#FFEDD5]"
            : "border-[#E2E8F0] bg-white text-[#1E293B] hover:bg-[#F8FAFC] hover:border-[#CBD5E1]",
          checking && "opacity-60 cursor-not-allowed"
        )}
      >
        {checking ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : hasAlert ? (
          <BellRing className="h-4 w-4" />
        ) : (
          <Bell className="h-4 w-4" />
        )}
        {hasAlert
          ? `Alert active at ${formatPrice(existingAlert.targetPrice)}`
          : "Set Price Alert"}
      </button>

      {/* ── Dialog ──────────────────────────────────────────── */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle className="text-[#1E293B]">
              {hasAlert && !editing ? "Price Alert Active" : "Set Price Alert"}
            </DialogTitle>
            <DialogDescription className="text-[#64748B]">
              {hasAlert && !editing
                ? "You'll be notified when the price drops to your target."
                : "We'll notify you when the price drops to your target."}
            </DialogDescription>
          </DialogHeader>

          {/* ── Current price ────────────────────────────────── */}
          <div className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] px-4 py-3">
            <span className="text-xs font-medium text-[#64748B]">
              Current price
            </span>
            <p className="text-lg font-bold text-[#1E293B]">
              {formatPrice(currentPrice)}
            </p>
          </div>

          {hasAlert && !editing ? (
            /* ── Existing alert view ─────────────────────────── */
            <div className="space-y-4">
              <div className="rounded-lg border border-[#F97316]/20 bg-[#FFF7ED] px-4 py-3">
                <span className="text-xs font-medium text-[#64748B]">
                  Alert target
                </span>
                <p className="text-lg font-bold text-[#F97316]">
                  {formatPrice(existingAlert.targetPrice)}
                </p>
                {existingAlert.marketplace && (
                  <p className="mt-0.5 text-xs text-[#64748B]">
                    on{" "}
                    {marketplaces.find(
                      (m) => m.slug === existingAlert.marketplace
                    )?.name ?? existingAlert.marketplace}
                  </p>
                )}
              </div>

              {/* Edit / Delete actions */}
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setEditing(true)}
                  className={cn(
                    "flex flex-1 items-center justify-center gap-2 rounded-lg border border-[#E2E8F0] bg-white px-4 py-2.5 text-sm font-medium text-[#1E293B] transition-colors",
                    "hover:bg-[#F8FAFC]",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-1"
                  )}
                >
                  <Pencil className="h-3.5 w-3.5" />
                  Edit
                </button>
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={deleting}
                  className={cn(
                    "flex flex-1 items-center justify-center gap-2 rounded-lg border border-red-200 bg-white px-4 py-2.5 text-sm font-medium text-red-600 transition-colors",
                    "hover:bg-red-50",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-1",
                    "disabled:cursor-not-allowed disabled:opacity-60"
                  )}
                >
                  {deleting ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="h-3.5 w-3.5" />
                  )}
                  Delete
                </button>
              </div>
            </div>
          ) : (
            /* ── Create / Edit form ──────────────────────────── */
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Target price */}
              <div>
                <label
                  htmlFor="target-price"
                  className="block text-sm font-medium text-[#1E293B]"
                >
                  Target price
                </label>
                <div className="relative mt-1.5">
                  <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-medium text-[#64748B]">
                    ₹
                  </span>
                  <input
                    id="target-price"
                    type="number"
                    min={1}
                    step={1}
                    value={targetPrice}
                    onChange={(e) => {
                      setTargetPrice(e.target.value);
                      setError(null);
                    }}
                    placeholder="Enter target price"
                    className={cn(
                      "w-full rounded-lg border bg-white py-2.5 pl-7 pr-3 text-sm text-[#1E293B]",
                      "placeholder:text-[#94A3B8]",
                      "focus:outline-none focus:ring-2 focus:ring-offset-0 transition-colors",
                      error
                        ? "border-red-300 focus:border-red-400 focus:ring-red-200"
                        : "border-[#E2E8F0] focus:border-[#F97316] focus:ring-[#F97316]/20"
                    )}
                  />
                </div>
              </div>

              {/* Marketplace */}
              <div>
                <label className="block text-sm font-medium text-[#1E293B]">
                  Marketplace
                </label>
                <Select
                  value={marketplace}
                  onValueChange={(v) => setMarketplace(v)}
                >
                  <SelectTrigger
                    className={cn(
                      "mt-1.5 w-full rounded-lg border-[#E2E8F0] text-sm text-[#1E293B]",
                      "focus:ring-2 focus:ring-[#F97316]/20 focus:ring-offset-0"
                    )}
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any" className="text-sm">
                      Any marketplace
                    </SelectItem>
                    {marketplaces.map((m) => (
                      <SelectItem
                        key={m.slug}
                        value={m.slug}
                        className="text-sm"
                      >
                        {m.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Error */}
              {error && (
                <p className="text-sm text-red-600">{error}</p>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={submitting}
                className={cn(
                  "w-full rounded-lg py-2.5 text-sm font-semibold text-white transition-colors",
                  "bg-[#F97316] hover:bg-[#EA580C]",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2",
                  "disabled:cursor-not-allowed disabled:opacity-60"
                )}
              >
                {submitting ? (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {editing ? "Updating…" : "Setting alert…"}
                  </span>
                ) : editing ? (
                  "Update Alert"
                ) : (
                  "Set Alert"
                )}
              </button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
