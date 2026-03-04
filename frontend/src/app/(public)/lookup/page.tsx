"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { productsApi } from "@/lib/api/products";
import { Search, ExternalLink, Loader2, AlertCircle } from "lucide-react";

/**
 * Domain → marketplace slug mapping.
 * Covers all 14 supported Indian marketplaces.
 */
const DOMAIN_TO_SLUG: Record<string, string> = {
  "amazon.in": "amazon_in",
  "www.amazon.in": "amazon_in",
  "flipkart.com": "flipkart",
  "www.flipkart.com": "flipkart",
  "myntra.com": "myntra",
  "www.myntra.com": "myntra",
  "nykaa.com": "nykaa",
  "www.nykaa.com": "nykaa",
  "snapdeal.com": "snapdeal",
  "www.snapdeal.com": "snapdeal",
  "croma.com": "croma",
  "www.croma.com": "croma",
  "reliancedigital.in": "reliance_digital",
  "www.reliancedigital.in": "reliance_digital",
  "ajio.com": "ajio",
  "www.ajio.com": "ajio",
  "meesho.com": "meesho",
  "www.meesho.com": "meesho",
  "tatacliq.com": "tatacliq",
  "www.tatacliq.com": "tatacliq",
  "jiomart.com": "jiomart",
  "www.jiomart.com": "jiomart",
  "vijaysales.com": "vijaysales",
  "www.vijaysales.com": "vijaysales",
  "firstcry.com": "firstcry",
  "www.firstcry.com": "firstcry",
  "giva.co": "giva",
  "www.giva.co": "giva",
};

/**
 * External ID extraction patterns per marketplace slug.
 * Each entry is a list of regex patterns — first match wins.
 */
const EXTERNAL_ID_PATTERNS: Record<string, RegExp[]> = {
  amazon_in: [
    /\/dp\/([A-Z0-9]{10})/,
    /\/gp\/product\/([A-Z0-9]{10})/,
  ],
  flipkart: [
    /\/p\/([a-zA-Z0-9]+)(?:\?|$)/,
  ],
  myntra: [
    /\/(\d+)\/buy/,
  ],
  nykaa: [
    /\/p\/(\d+)/,
  ],
  snapdeal: [
    /\/product\/\d+\/(\d+)/,
  ],
  croma: [
    /\/p\/(\d+)/,
  ],
  reliance_digital: [
    /\/(\d+p)/,
  ],
  ajio: [
    /\/p\/([a-zA-Z0-9]+)/,
  ],
  meesho: [
    /\/(\d+)(?:\?|$)/,
  ],
  tatacliq: [
    /\/p\/([a-zA-Z0-9-]+)/,
  ],
  jiomart: [
    /\/p\/(\d+)/,
  ],
  vijaysales: [
    /\/([a-zA-Z0-9-]+?)(?:\.html)?(?:\?|$)/,
  ],
  firstcry: [
    /\/product\/(\d+)/,
  ],
  giva: [
    /\/products\/([a-zA-Z0-9-]+)/,
  ],
};

interface ParsedUrl {
  marketplace: string;
  externalId: string;
}

/**
 * Parse a shopping URL to extract marketplace slug and external product ID.
 */
function parseShoppingUrl(rawUrl: string): ParsedUrl | null {
  try {
    const url = new URL(rawUrl);
    const slug = DOMAIN_TO_SLUG[url.hostname];
    if (!slug) return null;

    const patterns = EXTERNAL_ID_PATTERNS[slug];
    if (!patterns) return null;

    const fullPath = url.pathname + url.search;
    for (const pattern of patterns) {
      const match = fullPath.match(pattern);
      if (match?.[1]) {
        return { marketplace: slug, externalId: match[1] };
      }
    }
    return null;
  } catch {
    return null;
  }
}

type LookupState =
  | { status: "parsing" }
  | { status: "looking_up"; marketplace: string; externalId: string }
  | { status: "redirecting"; slug: string }
  | { status: "not_found"; url: string; marketplace: string; externalId: string }
  | { status: "invalid_url"; url: string }
  | { status: "no_url" };

export default function LookupPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [state, setState] = useState<LookupState>({ status: "parsing" });

  const rawUrl = searchParams.get("url") ?? "";

  useEffect(() => {
    if (!rawUrl) {
      setState({ status: "no_url" });
      return;
    }

    const parsed = parseShoppingUrl(rawUrl);
    if (!parsed) {
      setState({ status: "invalid_url", url: rawUrl });
      return;
    }

    setState({ status: "looking_up", ...parsed });

    productsApi.lookup(parsed.marketplace, parsed.externalId).then((res) => {
      if (res.success && res.data?.slug) {
        setState({ status: "redirecting", slug: res.data.slug });
        router.replace(`/product/${res.data.slug}`);
      } else {
        setState({
          status: "not_found",
          url: rawUrl,
          marketplace: parsed.marketplace,
          externalId: parsed.externalId,
        });
      }
    }).catch(() => {
      setState({
        status: "not_found",
        url: rawUrl,
        marketplace: parsed.marketplace,
        externalId: parsed.externalId,
      });
    });
  }, [rawUrl, router]);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-2xl px-4 py-16 sm:py-24">
        {state.status === "parsing" && <LoadingCard message="Reading URL..." />}
        {state.status === "looking_up" && <LoadingCard message="Looking up product..." />}
        {state.status === "redirecting" && <LoadingCard message="Product found! Redirecting..." />}
        {state.status === "no_url" && <NoUrlCard />}
        {state.status === "invalid_url" && <InvalidUrlCard url={state.url} />}
        {state.status === "not_found" && (
          <NotFoundCard
            url={state.url}
            marketplace={state.marketplace}
            externalId={state.externalId}
          />
        )}
      </main>
      <Footer />
    </>
  );
}

function LoadingCard({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center gap-4 rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
      <Loader2 className="h-8 w-8 animate-spin text-[#F97316]" />
      <p className="text-lg font-medium text-[#1E293B]">{message}</p>
    </div>
  );
}

function NoUrlCard() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#FFF7ED]">
          <ExternalLink className="h-6 w-6 text-[#F97316]" />
        </div>
        <h1 className="text-2xl font-bold text-[#1E293B]">Whydud URL Prefix</h1>
        <p className="text-[#64748B]">
          Prepend <span className="font-mono font-medium text-[#1E293B]">whydud.</span> to
          any shopping URL to instantly research the product.
        </p>
        <div className="mt-2 w-full rounded-md border border-slate-200 bg-[#F8FAFC] p-4">
          <p className="text-sm font-medium text-[#64748B]">Example</p>
          <p className="mt-1 font-mono text-sm text-[#1E293B]">
            <span className="text-[#F97316]">whydud.</span>amazon.in/dp/B0CZLQT2GG
          </p>
          <p className="mt-1 font-mono text-sm text-[#1E293B]">
            <span className="text-[#F97316]">whydud.</span>flipkart.com/p/itm123abc
          </p>
        </div>
        <p className="mt-2 text-sm text-[#64748B]">
          Works with Amazon, Flipkart, Myntra, Croma, and 10+ more Indian marketplaces.
        </p>
      </div>
    </div>
  );
}

function InvalidUrlCard({ url }: { url: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#FEE2E2]">
          <AlertCircle className="h-6 w-6 text-[#DC2626]" />
        </div>
        <h1 className="text-xl font-bold text-[#1E293B]">Unsupported URL</h1>
        <p className="text-[#64748B]">
          We couldn&apos;t recognize a product in this URL:
        </p>
        <p className="break-all rounded-md bg-[#F8FAFC] px-3 py-2 font-mono text-sm text-[#64748B]">
          {url}
        </p>
        <p className="text-sm text-[#64748B]">
          Make sure the URL is from a supported marketplace and contains a product page.
        </p>
        <a
          href="/search"
          className="mt-2 inline-flex items-center gap-2 rounded-md bg-[#F97316] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#EA580C] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2"
        >
          <Search className="h-4 w-4" />
          Search products instead
        </a>
      </div>
    </div>
  );
}

function NotFoundCard({
  url,
  marketplace,
  externalId,
}: {
  url: string;
  marketplace: string;
  externalId: string;
}) {
  // Format marketplace slug for display
  const marketplaceName = marketplace.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#FFF7ED]">
          <Search className="h-6 w-6 text-[#F97316]" />
        </div>
        <h1 className="text-xl font-bold text-[#1E293B]">Product Not in Our Database Yet</h1>
        <p className="text-[#64748B]">
          We found a product ID <span className="font-mono font-medium">{externalId}</span> on{" "}
          <span className="font-medium">{marketplaceName}</span>, but it&apos;s not in our database
          yet.
        </p>

        <div className="mt-2 flex w-full flex-col gap-3">
          <a
            href={`/search?q=${encodeURIComponent(externalId)}`}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-[#F97316] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#EA580C] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2"
          >
            <Search className="h-4 w-4" />
            Search for similar products
          </a>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-200 bg-white px-5 py-2.5 text-sm font-medium text-[#1E293B] transition-colors hover:bg-[#F8FAFC] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] focus-visible:ring-offset-2"
          >
            <ExternalLink className="h-4 w-4" />
            View on {marketplaceName}
          </a>
        </div>

        <p className="mt-4 text-xs text-[#94A3B8]">
          We&apos;re constantly adding products. Check back soon or search for it by name.
        </p>
      </div>
    </div>
  );
}
