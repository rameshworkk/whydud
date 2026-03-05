"use client";

import { useState, useEffect, useCallback } from "react";
import { SlidersHorizontal } from "lucide-react";
import { preferencesApi } from "@/lib/api/preferences";
import { CategorySelector } from "@/components/preferences/category-selector";
import { PreferenceForm } from "@/components/preferences/preference-form";
import type { PreferenceSchema, PurchasePreference } from "@/lib/api/types";

// ── Skeletons ────────────────────────────────────────────────────────────────

function CategoryCardSkeleton() {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-[#E2E8F0] bg-white p-4 animate-pulse">
      <div className="h-10 w-10 rounded-lg bg-slate-200" />
      <div className="h-3 w-16 rounded bg-slate-200" />
    </div>
  );
}

function FormSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-lg border border-[#E2E8F0] bg-white p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-9 w-9 rounded-lg bg-slate-200" />
            <div className="h-4 w-32 rounded bg-slate-200" />
          </div>
          <div className="space-y-4">
            <div className="h-3 w-20 rounded bg-slate-200" />
            <div className="h-10 w-full rounded-lg bg-slate-100" />
            <div className="h-3 w-24 rounded bg-slate-200" />
            <div className="flex gap-2">
              <div className="h-8 w-20 rounded-full bg-slate-100" />
              <div className="h-8 w-24 rounded-full bg-slate-100" />
              <div className="h-8 w-16 rounded-full bg-slate-100" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function PreferencesPage() {
  const [schemas, setSchemas] = useState<PreferenceSchema[]>([]);
  const [savedPrefs, setSavedPrefs] = useState<PurchasePreference[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [activeSchema, setActiveSchema] = useState<PreferenceSchema | null>(null);
  const [loadingSchemas, setLoadingSchemas] = useState(true);
  const [loadingForm, setLoadingForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Fetch all schemas + user's saved preferences on mount
  useEffect(() => {
    async function load() {
      try {
        const [schemasRes, prefsRes] = await Promise.all([
          preferencesApi.listSchemas(),
          preferencesApi.list(),
        ]);

        if (schemasRes.success && "data" in schemasRes) {
          setSchemas(schemasRes.data);
        }
        if (prefsRes.success && "data" in prefsRes) {
          setSavedPrefs(prefsRes.data);
        }
      } catch {
        setError("Failed to load preferences.");
      } finally {
        setLoadingSchemas(false);
      }
    }
    load();
  }, []);

  // When a category is selected, fetch its schema detail
  const handleSelectCategory = useCallback(
    async (slug: string) => {
      if (slug === selectedSlug) {
        // Deselect
        setSelectedSlug(null);
        setActiveSchema(null);
        return;
      }

      setSelectedSlug(slug);
      setActiveSchema(null);
      setLoadingForm(true);
      setError(null);
      setSuccessMessage(null);

      try {
        const res = await preferencesApi.getSchema(slug);
        if (res.success && "data" in res) {
          setActiveSchema(res.data);
        } else if (!res.success && "error" in res) {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to load preference schema.");
      } finally {
        setLoadingForm(false);
      }
    },
    [selectedSlug]
  );

  // Submit / update preferences
  const handleSubmit = useCallback(
    async (values: Record<string, unknown>) => {
      if (!selectedSlug) return;
      setSubmitting(true);
      setError(null);
      setSuccessMessage(null);

      try {
        const existingPref = savedPrefs.find(
          (p) => p.categorySlug === selectedSlug
        );

        const payload = { preferences: values };
        const res = existingPref
          ? await preferencesApi.update(selectedSlug, payload)
          : await preferencesApi.save(selectedSlug, payload);

        if (res.success && "data" in res) {
          // Update local saved prefs list
          setSavedPrefs((prev) => {
            const filtered = prev.filter(
              (p) => p.categorySlug !== selectedSlug
            );
            return [...filtered, res.data];
          });
          setSuccessMessage(
            existingPref
              ? "Preferences updated successfully!"
              : "Preferences saved successfully!"
          );
          // Auto-dismiss success message
          setTimeout(() => setSuccessMessage(null), 4000);
        } else if (!res.success && "error" in res) {
          setError(res.error.message);
        }
      } catch {
        setError("Failed to save preferences.");
      } finally {
        setSubmitting(false);
      }
    },
    [selectedSlug, savedPrefs]
  );

  // Get initial values for the form from saved preferences
  const initialValues =
    selectedSlug
      ? savedPrefs.find((p) => p.categorySlug === selectedSlug)?.preferences
      : undefined;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#FFF7ED]">
            <SlidersHorizontal className="h-5 w-5 text-[#F97316]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#1E293B]">
              Purchase Preferences
            </h1>
            <p className="text-sm text-[#64748B]">
              Tell us what you need — we'll personalize recommendations,
              scores, and alerts.
            </p>
          </div>
        </div>
      </div>

      {/* Category selector */}
      {loadingSchemas ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {Array.from({ length: 7 }).map((_, i) => (
            <CategoryCardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <CategorySelector
          schemas={schemas}
          savedPreferences={savedPrefs}
          selectedSlug={selectedSlug}
          onSelect={handleSelectCategory}
        />
      )}

      {/* Error / Success messages */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {successMessage && (
        <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-[#16A34A]">
          {successMessage}
        </div>
      )}

      {/* Preference form */}
      {selectedSlug && (
        <div className="max-w-2xl">
          {loadingForm ? (
            <FormSkeleton />
          ) : activeSchema ? (
            <>
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-[#1E293B]">
                  {activeSchema.categoryName} Preferences
                </h2>
                <p className="text-sm text-[#64748B]">
                  {initialValues
                    ? "Update your preferences below."
                    : "Fill in your requirements to get personalized recommendations."}
                </p>
              </div>
              <PreferenceForm
                key={activeSchema.categorySlug}
                schema={activeSchema}
                initialValues={initialValues as Record<string, unknown> | undefined}
                onSubmit={handleSubmit}
                submitting={submitting}
              />
            </>
          ) : null}
        </div>
      )}

      {/* Empty state when no category selected */}
      {!selectedSlug && !loadingSchemas && schemas.length > 0 && (
        <div className="rounded-lg border border-[#E2E8F0] bg-white px-6 py-12 text-center">
          <SlidersHorizontal className="mx-auto h-10 w-10 text-[#94A3B8]" />
          <p className="mt-3 text-sm font-medium text-[#64748B]">
            Select a category above to set your preferences
          </p>
          <p className="mt-1 text-xs text-[#94A3B8]">
            Your preferences help us find the best products for your needs
          </p>
        </div>
      )}
    </div>
  );
}
