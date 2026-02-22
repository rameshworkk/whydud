"use client";

// TODO Sprint 4 Week 10: Wire to /api/v1/tco/models/:category_slug
interface TCOCalculatorProps {
  productSlug: string;
  categorySlug: string;
}

/** TCO Calculator widget on product pages. Lazy-loaded. */
export function TCOCalculator({ productSlug, categorySlug }: TCOCalculatorProps) {
  return (
    <div className="rounded-xl border bg-card p-6">
      <h3 className="font-bold text-lg mb-1">Total Cost of Ownership</h3>
      <p className="text-sm text-muted-foreground mb-4">
        How much will this really cost over 5 years?
      </p>

      {/* TODO Sprint 4: City selector, usage inputs, and TCO breakdown chart */}
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium">Your city</label>
          <select className="rounded-md border bg-background px-3 py-2 text-sm" disabled>
            <option>Select city — coming Sprint 4</option>
          </select>
        </div>
        <div className="h-32 rounded-lg bg-muted flex items-center justify-center text-sm text-muted-foreground">
          TCO breakdown chart — Sprint 4
        </div>
      </div>
    </div>
  );
}
