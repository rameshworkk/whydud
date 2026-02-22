"use client";

import type { PaymentMethod } from "@/types";

interface CardVaultProps {
  cards: PaymentMethod[];
  isLoading?: boolean;
  onAdd: () => void;
  onRemove: (id: string) => void;
}

/** Card vault UI — bank name + variant only, never card numbers. */
export function CardVault({ cards, isLoading, onAdd, onRemove }: CardVaultProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {cards.map((card) => (
        <div key={card.id} className="flex items-center gap-3 rounded-xl border bg-card px-4 py-3">
          <div className="flex-1">
            <p className="font-medium text-sm">
              {card.bankName} {card.cardVariant}
            </p>
            <p className="text-xs text-muted-foreground capitalize">
              {card.methodType.replace("_", " ")}
              {card.cardNetwork ? ` · ${card.cardNetwork}` : ""}
            </p>
          </div>
          {card.isPreferred && (
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
              Preferred
            </span>
          )}
          <button
            onClick={() => onRemove(card.id)}
            className="text-xs text-muted-foreground hover:text-destructive"
            aria-label="Remove card"
          >
            Remove
          </button>
        </div>
      ))}

      <button
        onClick={onAdd}
        className="flex items-center justify-center gap-2 rounded-xl border-2 border-dashed py-3 text-sm text-muted-foreground hover:border-primary hover:text-primary transition-colors"
      >
        + Add payment method
      </button>

      <p className="text-xs text-muted-foreground text-center">
        We store bank name and card variant only — no card numbers, ever.
      </p>
    </div>
  );
}
