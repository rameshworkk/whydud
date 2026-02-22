"use client";

import { useState } from "react";
import type { InboxEmail } from "@/types";
import { InboxSidebar } from "@/components/inbox/InboxSidebar";
import { EmailList } from "@/components/inbox/EmailList";

// TODO Sprint 3 Week 8: fetch emails server-side or via SWR
export default function InboxPage() {
  const [activeFolder, setActiveFolder] = useState("all");
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);

  const emails: InboxEmail[] = []; // placeholder — API not yet implemented

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">Inbox</h1>

      <div className="flex gap-0 rounded-2xl border overflow-hidden min-h-[600px]">
        {/* Sidebar */}
        <div className="w-48 shrink-0 border-r bg-muted/20">
          <InboxSidebar activeFolder={activeFolder} onFolderChange={setActiveFolder} />
        </div>

        {/* Email list */}
        <div className="w-64 shrink-0 border-r overflow-y-auto">
          <EmailList
            emails={emails}
            selectedId={selectedEmailId}
            onSelect={setSelectedEmailId}
          />
        </div>

        {/* Email reader */}
        <div className="flex-1 p-6 flex items-center justify-center text-sm text-muted-foreground">
          {selectedEmailId ? (
            <p>TODO Sprint 3: Email reader for {selectedEmailId}</p>
          ) : (
            <p>Select an email to read</p>
          )}
        </div>
      </div>
    </div>
  );
}
