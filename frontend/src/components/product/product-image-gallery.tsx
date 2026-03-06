"use client";

import { useState } from "react";

interface ProductImageGalleryProps {
  images: string[];
  title: string;
}

const FALLBACK_IMAGE = "https://placehold.co/400x500/e8f4fd/1e40af?text=No+Image";

export function ProductImageGallery({ images, title }: ProductImageGalleryProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const mainImage = images[selectedIndex] ?? FALLBACK_IMAGE;

  return (
    <div className="p-4 border-b border-slate-100">
      <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-slate-50 border border-slate-100 flex items-center justify-center">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={mainImage}
          alt={title}
          className="object-contain p-4 w-full h-full"
        />
      </div>
      {images.length > 1 && (
        <div className="flex gap-2 mt-3">
          {images.slice(0, 4).map((img, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setSelectedIndex(i)}
              className={`w-14 h-14 rounded-lg border-2 overflow-hidden transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F97316] ${
                i === selectedIndex ? "border-[#F97316]" : "border-slate-200 hover:border-slate-300"
              }`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={img}
                alt={`View ${i + 1}`}
                className="object-contain p-1 w-full h-full"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
