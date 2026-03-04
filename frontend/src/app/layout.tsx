import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "sonner";
import { AuthProvider } from "@/contexts/auth-context";
import { CompareProvider } from "@/contexts/compare-context";
import { CompareTray } from "@/components/compare/compare-tray";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Whydud — India's Product Intelligence Platform",
    template: "%s | Whydud",
  },
  description:
    "Don't buy a dud. Check DudScore, price history, fake review detection, and personalized card offers before buying.",
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://whydud.com"),
  openGraph: {
    siteName: "Whydud",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className={inter.variable}>
      <body className="min-h-screen bg-[#F8FAFC] font-sans antialiased">
        <AuthProvider>
          <CompareProvider>
            {children}
            <CompareTray />
            <Toaster
              position="top-center"
              toastOptions={{
                style: {
                  fontFamily: "var(--font-inter), sans-serif",
                },
              }}
            />
          </CompareProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
