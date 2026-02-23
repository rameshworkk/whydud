import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { sellersApi } from "@/lib/api/sellers";

interface SellerPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: SellerPageProps): Promise<Metadata> {
  const { slug } = await params;
  const res = await sellersApi.getDetail(slug).catch(() => null);
  const name = res?.success ? res.data.name : "Seller";
  return { title: `${name} — Whydud` };
}

/** Mini TrustScore gauge — same approach as DudScoreGauge but smaller. */
function TrustScoreGauge({ score }: { score: number }) {
  const cx = 50;
  const cy = 48;
  const r = 38;
  const strokeW = 8;
  const x0 = cx - r;
  const x1 = cx + r;
  const needleAngle = Math.PI * (1 - score / 100);
  const nx = cx + r * Math.cos(needleAngle);
  const ny = cy - r * Math.sin(needleAngle);

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 100 58" className="w-[90px]">
        <defs>
          <linearGradient id="trust-grad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#DC2626" />
            <stop offset="50%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#16A34A" />
          </linearGradient>
        </defs>
        <path
          d={`M ${x0},${cy} A ${r},${r} 0 0 1 ${x1},${cy}`}
          fill="none"
          stroke="#E2E8F0"
          strokeWidth={strokeW}
          strokeLinecap="round"
        />
        <path
          d={`M ${x0},${cy} A ${r},${r} 0 0 1 ${x1},${cy}`}
          fill="none"
          stroke="url(#trust-grad)"
          strokeWidth={strokeW}
          strokeLinecap="round"
          pathLength="1"
          strokeDasharray="1"
          strokeDashoffset={1 - score / 100}
        />
        <circle cx={nx} cy={ny} r="3" fill="#1E293B" />
        <text
          x={cx}
          y={cy - 4}
          textAnchor="middle"
          fontSize="16"
          fontWeight="800"
          fill="#1E293B"
          fontFamily="Inter, system-ui, sans-serif"
        >
          {score}%
        </text>
      </svg>
      <span className="text-xs text-slate-500 font-medium mt-0.5">
        Seller Trustscore
      </span>
    </div>
  );
}

export default async function SellerPage({ params }: SellerPageProps) {
  const { slug } = await params;
  const res = await sellersApi.getDetail(slug).catch(() => null);
  if (!res?.success) notFound();

  const s = res.data;

  const tabs = [
    "Seller info",
    "Reviews",
    "Return, Refund and Cancellation policy",
    "Product Catalog",
  ];

  return (
    <>
      <Header />
      <main className="mx-auto max-w-[1280px] px-4 py-6">
        <div className="flex gap-6">
          {/* Left content */}
          <div className="flex-1 min-w-0">
            {/* Seller header card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 mb-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={s.avatarUrl}
                    alt={s.name}
                    className="w-16 h-16 rounded-xl border border-slate-200 shrink-0"
                  />
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h1 className="text-xl font-bold text-slate-900">
                        {s.name}
                      </h1>
                      {s.isVerified && (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
                          ✓ Verified seller
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div className="flex gap-0.5">
                        {Array.from({ length: 5 }, (_, i) => (
                          <span
                            key={i}
                            className={`text-base ${
                              i < Math.round(s.avgRating ?? 0)
                                ? "text-yellow-400"
                                : "text-slate-200"
                            }`}
                          >
                            ★
                          </span>
                        ))}
                      </div>
                      <span className="text-sm font-semibold text-slate-700">
                        {s.avgRating ?? "—"}
                      </span>
                      <span className="text-sm text-slate-400 mx-1">·</span>
                      <span className="text-sm text-slate-500">
                        {s.productCount} Products
                      </span>
                      <span className="text-sm text-slate-400 mx-1">·</span>
                      <span className="text-sm text-slate-500">
                        Seller since {s.sellerSince}
                      </span>
                    </div>
                  </div>
                </div>
                {s.trustScore != null && (
                  <TrustScoreGauge score={s.trustScore} />
                )}
              </div>
            </div>

            {/* Tab bar */}
            <div className="flex gap-2 mb-6 overflow-x-auto no-scrollbar">
              {tabs.map((tab, i) => (
                <button
                  key={tab}
                  className={`shrink-0 px-4 py-2 rounded-full text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] ${
                    i === 0
                      ? "bg-[#F97316] text-white"
                      : "border border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Seller info tab content */}
            <div className="space-y-6">
              <p className="text-base text-slate-600 leading-relaxed">
                {s.description}
              </p>

              {s.categories.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-800 mb-3">
                    Product Categories
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {s.categories.map((cat) => (
                      <span
                        key={cat}
                        className="px-3 py-1.5 rounded-full border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 cursor-pointer transition-colors"
                      >
                        {cat}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {s.photoCount > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-800 mb-3">
                    Customer photos &amp; videos
                  </h3>
                  <div className="flex gap-2 overflow-x-auto no-scrollbar">
                    {Array.from({ length: s.photoCount }, (_, i) => (
                      <div
                        key={i}
                        className="w-16 h-16 rounded-lg bg-slate-200 shrink-0"
                      />
                    ))}
                  </div>
                </div>
              )}

              {s.socials.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-800 mb-3">
                    Socials
                  </h3>
                  <div className="flex gap-2">
                    {s.socials.map((social) => (
                      <a
                        key={social.label}
                        href={social.url}
                        className="px-3 py-1.5 rounded-full bg-slate-100 text-sm text-slate-600 hover:bg-slate-200 transition-colors"
                      >
                        {social.label}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {s.contact.address.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-800 mb-2">
                    Contact
                  </h3>
                  <div className="text-sm text-slate-500 leading-relaxed">
                    {s.contact.address.map((line) => (
                      <p key={line}>{line}</p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right sidebar */}
          <aside className="w-[320px] shrink-0 hidden lg:flex flex-col gap-4">
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <h2 className="text-base font-bold text-slate-900 mb-1">
                Seller Performance
              </h2>
              <p className="text-xs text-slate-400 mb-4">
                {s.performance.positiveReviewPct}% positive reviews in{" "}
                {s.performance.reviewPeriod}
              </p>
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <span className="text-slate-400">⏱</span>
                    Avg Resolution Time
                  </div>
                  <span className="text-sm font-semibold text-green-600">
                    {s.performance.avgResolutionTime}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <span className="text-slate-400">🔄</span>
                    Turnaround Time
                  </div>
                  <span className="text-sm font-semibold text-[#F97316]">
                    {s.performance.turnaroundTime}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <span className="text-slate-400">💬</span>
                    Response Rate
                  </div>
                  <span className="text-sm font-semibold text-green-600">
                    {s.performance.responseRate}
                  </span>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-bold text-slate-900">
                  Report or enquire an issue
                </h3>
                <span className="text-slate-400 text-lg">⚠</span>
              </div>
              <p className="text-xs text-slate-500 mb-4">
                Report an issue about an experience you had with this store.
              </p>
              <div className="flex flex-col gap-2">
                <button className="w-full py-2 rounded-full border border-[#4DB6AC] text-sm font-semibold text-[#4DB6AC] hover:bg-teal-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#4DB6AC]">
                  Report an issue
                </button>
                <button className="w-full py-2 rounded-full border border-[#4DB6AC] text-sm font-semibold text-[#4DB6AC] hover:bg-teal-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#4DB6AC]">
                  Enquire about an issue
                </button>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <h3 className="text-sm font-bold text-slate-900">
                Write seller feedback
              </h3>
            </div>
          </aside>
        </div>
      </main>
      <Footer />
    </>
  );
}
