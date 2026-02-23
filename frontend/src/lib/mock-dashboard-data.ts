/**
 * Mock data for the Expense Tracker dashboard.
 * All monetary values in paisa (integer).
 */

export interface DashboardStat {
  label: string;
  value: string;
  icon: "spend" | "orders" | "average" | "platform";
}

export interface MonthlySpendPoint {
  week: string;
  amount: number; // paisa
}

export interface PlatformSpend {
  name: string;
  amount: number; // paisa
  color: string;
}

export interface CategorySpend {
  name: string;
  amount: number; // paisa
  percentage: number;
  color: string;
}

export interface InsightCard {
  title: string;
  description: string;
  icon: string;
}

export const MOCK_DASHBOARD_STATS: DashboardStat[] = [
  { label: "Total spend", value: "₹1,25,075", icon: "spend" },
  { label: "Orders", value: "42", icon: "orders" },
  { label: "Average order", value: "₹2,978", icon: "average" },
  { label: "Top platform", value: "Amazon", icon: "platform" },
];

export const MOCK_MONTHLY_SPEND = {
  total: "₹1,25,075",
  change: "+3.2%",
  changePositive: true,
  subtitle: "Your spending across the last 4 weeks",
  data: [
    { week: "Week 1", amount: 3200000 },
    { week: "Week 2", amount: 2800000 },
    { week: "Week 3", amount: 3500000 },
    { week: "Week 4", amount: 2600000 },
  ] as MonthlySpendPoint[],
};

export const MOCK_PLATFORM_SPEND: PlatformSpend[] = [
  { name: "Amazon", amount: 5000000, color: "#4F46E5" },
  { name: "Flipkart", amount: 3200000, color: "#7C3AED" },
  { name: "Others", amount: 1800000, color: "#D1D5DB" },
];

export const MOCK_CATEGORY_SPEND = {
  total: "₹1,25,075",
  change: "+1.5%",
  changePositive: true,
  categories: [
    { name: "Fashion", amount: 4000000, percentage: 40, color: "#4F46E5" },
    { name: "Electronics", amount: 3000000, percentage: 30, color: "#7C3AED" },
    { name: "Groceries", amount: 2000000, percentage: 20, color: "#A78BFA" },
    { name: "Home", amount: 1000000, percentage: 10, color: "#C4B5FD" },
  ] as CategorySpend[],
};

export const MOCK_INSIGHTS: InsightCard[] = [
  {
    title: "Your biggest platform is Amazon",
    description:
      "You've spent a total of ₹50,000 on this platform this month.",
    icon: "trending",
  },
  {
    title: "Electronics is your top category",
    description:
      "Your spending on Electronics increased by 16% this month.",
    icon: "category",
  },
  {
    title: "Friday is your biggest spending day",
    description:
      "You tend to spend 30% more on Fridays compared to other days.",
    icon: "calendar",
  },
];

export const DASHBOARD_TABS = [
  "Overview",
  "Platforms",
  "Categories",
  "Timeline",
  "Insights",
] as const;
