"use client";

// TODO Sprint 1 Week 3: dynamic category-specific filters
interface SearchFiltersProps {
  onFilterChange: (key: string, value: string) => void;
}

/** Sidebar filter panel for search results. */
export function SearchFilters({ onFilterChange }: SearchFiltersProps) {
  return (
    <aside className="flex flex-col gap-6 text-sm">
      <div>
        <h3 className="font-semibold mb-2">Sort by</h3>
        <select
          className="w-full rounded-md border bg-background px-3 py-2"
          onChange={(e) => onFilterChange("sortBy", e.target.value)}
        >
          <option value="relevance">Relevance</option>
          <option value="dudscore">DudScore</option>
          <option value="price_asc">Price: Low to High</option>
          <option value="price_desc">Price: High to Low</option>
          <option value="newest">Newest</option>
        </select>
      </div>

      <div>
        <h3 className="font-semibold mb-2">DudScore</h3>
        <div className="flex flex-col gap-1">
          {[["70", "Good & above (70+)"], ["50", "Average & above (50+)"], ["30", "All rated"]].map(
            ([val, label]) => (
              <label key={val} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="minDudScore"
                  value={val}
                  onChange={(e) => onFilterChange("minDudScore", e.target.value)}
                />
                {label}
              </label>
            )
          )}
        </div>
      </div>

      <div>
        <h3 className="font-semibold mb-2">Availability</h3>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            onChange={(e) => onFilterChange("inStock", String(e.target.checked))}
          />
          In stock only
        </label>
      </div>
    </aside>
  );
}
