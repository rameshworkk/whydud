import type { Metadata } from "next";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "About Whydud",
  description: "India's product intelligence and trust platform.",
};

export default function AboutPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-bold text-[#1E293B] mb-6">About Whydud</h1>

        <div className="space-y-5 text-[#475569] leading-relaxed">
          <p>
            Whydud is India&apos;s product intelligence and trust platform. We help you
            make confident purchase decisions by aggregating prices, reviews, and
            seller data across 12+ Indian marketplaces.
          </p>

          <h2 className="text-xl font-semibold text-[#1E293B] pt-2">What we do</h2>
          <ul className="list-disc pl-5 space-y-2">
            <li>
              <strong>DudScore</strong> — a proprietary trust score that combines
              review sentiment, rating quality, price stability, and return signals
              into a single number so you know whether a product is worth your money.
            </li>
            <li>
              <strong>Price intelligence</strong> — track price history across
              marketplaces and get alerts when prices drop.
            </li>
            <li>
              <strong>Review credibility</strong> — we detect fake and incentivised
              reviews so you see only genuine opinions.
            </li>
            <li>
              <strong>Smart payment optimiser</strong> — find the best bank card
              offers and cashback deals for each purchase.
            </li>
          </ul>

          <h2 className="text-xl font-semibold text-[#1E293B] pt-2">Our mission</h2>
          <p>
            Don&apos;t buy a dud. We believe every Indian shopper deserves transparent,
            unbiased product information — free from inflated ratings and fake
            discounts.
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
