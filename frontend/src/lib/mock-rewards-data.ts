/**
 * Mock data for the Rewards page.
 */

export interface MockEarnCard {
  icon: string;
  title: string;
  points: number;
  description: string;
}

export interface MockGiftCard {
  id: string;
  brand: string;
  logo: string;
  denomination: number; // paisa
  pointsCost: number;
}

export interface MockPointsHistory {
  id: string;
  description: string;
  points: number; // positive = earned, negative = spent
  date: string;
}

export const MOCK_BALANCE = {
  currentBalance: 450,
  totalEarned: 1450,
  totalSpent: 1000,
  valueInRupees: 45,
  nextMilestone: 1000,
  nextMilestoneReward: "₹100 gift card",
};

export const MOCK_EARN_CARDS: MockEarnCard[] = [
  { icon: "✍️", title: "Write a Review", points: 20, description: "Write a review for a product you've purchased" },
  { icon: "📧", title: "Connect Email", points: 50, description: "Connect your shopping email to start tracking" },
  { icon: "👥", title: "Refer a Friend", points: 30, description: "Invite a friend to join Whydud" },
  { icon: "🔥", title: "Login Streak", points: 10, description: "Log in for 7 consecutive days" },
];

export const MOCK_GIFT_CARDS: MockGiftCard[] = [
  { id: "gc1", brand: "Amazon", logo: "🛒", denomination: 10000, pointsCost: 1000 },
  { id: "gc2", brand: "Flipkart", logo: "🛍️", denomination: 10000, pointsCost: 1000 },
  { id: "gc3", brand: "Swiggy", logo: "🍔", denomination: 10000, pointsCost: 1000 },
  { id: "gc4", brand: "Zomato", logo: "🍕", denomination: 10000, pointsCost: 1000 },
  { id: "gc5", brand: "BookMyShow", logo: "🎬", denomination: 20000, pointsCost: 2000 },
  { id: "gc6", brand: "Myntra", logo: "👗", denomination: 50000, pointsCost: 5000 },
];

export const MOCK_POINTS_HISTORY: MockPointsHistory[] = [
  { id: "ph1", description: "Review on OnePlus Nord 5", points: 20, date: "2026-02-22" },
  { id: "ph2", description: "Connected shopping email", points: 50, date: "2026-02-20" },
  { id: "ph3", description: "Redeemed Amazon ₹100 gift card", points: -1000, date: "2026-02-18" },
  { id: "ph4", description: "7-day login streak bonus", points: 10, date: "2026-02-15" },
  { id: "ph5", description: "Review on Samsung Galaxy S24 FE", points: 20, date: "2026-02-12" },
  { id: "ph6", description: "Referred Arnab Sen", points: 30, date: "2026-02-10" },
  { id: "ph7", description: "Welcome bonus", points: 100, date: "2026-02-01" },
];
