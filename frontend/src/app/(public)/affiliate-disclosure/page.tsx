import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "Affiliate Disclosure",
  description: "How Whydud earns revenue through affiliate partnerships.",
};

export default function AffiliateDisclosurePage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold text-[#1E293B] mb-6">Affiliate Disclosure</h1>

        <div className="space-y-5 text-[#475569] leading-relaxed">
          <p>
            Whydud participates in affiliate programs with multiple Indian
            e-commerce marketplaces, including Amazon.in, Flipkart, Croma, Myntra,
            and others.
          </p>

          <p>
            When you click on a product link on Whydud and make a purchase on a
            partner marketplace, we may earn a small commission at no additional
            cost to you. This revenue helps us keep the platform free and
            independent.
          </p>

          <h2 className="text-lg font-semibold text-[#1E293B] pt-2">
            Does this affect our recommendations?
          </h2>
          <p>
            No. DudScore, price comparisons, and review analysis are computed
            independently of affiliate partnerships. Our scoring algorithms do not
            favour products or marketplaces based on commission rates.
          </p>

          <h2 className="text-lg font-semibold text-[#1E293B] pt-2">
            How to identify affiliate links
          </h2>
          <p>
            All outbound links to marketplaces from product pages, deal cards, and
            price comparison tables are affiliate links. We clearly display the
            source marketplace name alongside each price.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
