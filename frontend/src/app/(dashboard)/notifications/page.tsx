import type { Metadata } from "next";
import { NotificationList } from "@/components/notifications/notification-list";

export const metadata: Metadata = {
  title: "Notifications — Whydud",
  description: "Price drops, order updates, review activity, and more.",
};

export default function NotificationsPage() {
  return <NotificationList />;
}
