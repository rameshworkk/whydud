"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { searchApi } from "@/lib/api/search";
import type { ProductSummary } from "@/types";

interface UseSearchReturn {
  query: string;
  setQuery: (q: string) => void;
  suggestions: Array<{ id: string; title: string; slug: string; categoryName: string }>;
  isLoadingSuggestions: boolean;
}

export function useSearchAutocomplete(debounceMs = 200): UseSearchReturn {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<UseSearchReturn["suggestions"]>([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (query.length < 2) {
      setSuggestions([]);
      return;
    }
    timerRef.current = setTimeout(async () => {
      setIsLoadingSuggestions(true);
      const res = await searchApi.autocomplete(query);
      if (res.success) setSuggestions(res.data);
      setIsLoadingSuggestions(false);
    }, debounceMs);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query, debounceMs]);

  return { query, setQuery, suggestions, isLoadingSuggestions };
}
