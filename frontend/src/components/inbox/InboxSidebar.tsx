"use client";

const FOLDERS = [
  { id: "all", label: "All Mail", icon: "📬" },
  { id: "order", label: "Orders", icon: "📦" },
  { id: "shipping", label: "Shipping", icon: "🚚" },
  { id: "refund", label: "Refunds", icon: "↩️" },
  { id: "return", label: "Returns", icon: "📮" },
  { id: "subscription", label: "Subscriptions", icon: "🔁" },
  { id: "promo", label: "Promotions", icon: "🏷️" },
  { id: "starred", label: "Starred", icon: "⭐" },
];

interface InboxSidebarProps {
  activeFolder: string;
  onFolderChange: (id: string) => void;
}

/** Two-panel inbox sidebar — folder list. */
export function InboxSidebar({ activeFolder, onFolderChange }: InboxSidebarProps) {
  return (
    <nav className="flex flex-col gap-1 p-2">
      {FOLDERS.map((folder) => (
        <button
          key={folder.id}
          onClick={() => onFolderChange(folder.id)}
          className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-left transition-colors ${
            activeFolder === folder.id
              ? "bg-primary text-primary-foreground"
              : "hover:bg-muted text-muted-foreground hover:text-foreground"
          }`}
        >
          <span>{folder.icon}</span>
          <span>{folder.label}</span>
        </button>
      ))}
    </nav>
  );
}
