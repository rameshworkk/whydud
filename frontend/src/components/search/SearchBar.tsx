"use client";

import { useRouter } from "next/navigation";
import { useSearchAutocomplete } from "@/hooks/useSearch";

/** Global search bar with autocomplete. */
export function SearchBar() {
  const router = useRouter();
  const { query, setQuery, suggestions, isLoadingSuggestions } = useSearchAutocomplete();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="relative flex-1 max-w-xl">
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search products… e.g. wireless earbuds under ₹2000"
        className="w-full rounded-full border bg-muted px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
        aria-label="Search products"
        autoComplete="off"
      />

      {/* Autocomplete dropdown */}
      {suggestions.length > 0 && (
        <ul className="absolute top-full left-0 right-0 z-50 mt-1 rounded-xl border bg-background shadow-lg overflow-hidden">
          {suggestions.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                className="w-full flex items-center gap-3 px-4 py-2 text-left text-sm hover:bg-muted"
                onClick={() => router.push(`/product/${s.slug}`)}
              >
                <span className="flex-1 truncate">{s.title}</span>
                <span className="text-xs text-muted-foreground">{s.categoryName}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
