PART 1: DESIGN SYSTEM (Extracted from Figma)
Brand Identity
Logo: 3D cube/package with question mark (teal + dark navy) + orange accent dot
Logotype: "Whydud" — Semi-bold, rounded sans-serif, dark navy (#2D3748 or similar)
Tagline: "Discover product truth. Shop smarter."
Color Palette
PRIMARY COLORS
  --color-primary:          #F97316  (Orange — CTAs, highlights, "Best buy" badges, active states)
  --color-primary-hover:    #EA580C  (Darker orange for hover)
  --color-primary-light:    #FFF7ED  (Orange tint backgrounds)
  
SECONDARY COLORS  
  --color-teal:             #4DB6AC  (Logo accent, secondary elements, DudScore gauge)
  --color-teal-dark:        #2D8E85  (Darker teal variant)
  --color-navy:             #1E293B  (Primary text, logo text, headers)
  --color-yellow:           #F59E0B  (Star ratings, warnings)
  --color-yellow-star:      #FBBF24  (Star fill color)

SEMANTIC COLORS
  --color-success:          #16A34A  (Green — good scores, price drops, "Best" labels)
  --color-success-light:    #DCFCE7  (Green badge backgrounds)
  --color-warning:          #F59E0B  (Yellow — medium scores, caution)
  --color-danger:           #DC2626  (Red — bad scores, "Dud" label, price increases)
  --color-danger-light:     #FEE2E2  (Red badge backgrounds)
  --color-info:             #3B82F6  (Blue — links, info badges)

NEUTRALS
  --color-bg-primary:       #FFFFFF  (Page background)
  --color-bg-secondary:     #F8FAFC  (Section backgrounds, card backgrounds)
  --color-bg-tertiary:      #F1F5F9  (Input backgrounds, sidebar, hover states)
  --color-border:           #E2E8F0  (Card borders, dividers)
  --color-border-light:     #F1F5F9  (Subtle borders)
  --color-text-primary:     #1E293B  (Headings, primary text)
  --color-text-secondary:   #64748B  (Secondary text, descriptions)
  --color-text-tertiary:    #94A3B8  (Placeholder text, timestamps)
  --color-text-inverse:     #FFFFFF  (Text on dark/colored backgrounds)

CATEGORY HEADER BAR (Homepage top)
  --color-category-bar:     #F97316  (Orange gradient bar with category icons)
Typography
FONT FAMILY
  Primary: Inter (or system sans-serif fallback)
  Headings: Inter Semi-Bold / Bold
  Body: Inter Regular / Medium
  Mono: JetBrains Mono (code, prices in some contexts)

SCALE (Mobile → Desktop)
  --text-xs:    0.75rem / 12px   (Badges, timestamps, small labels)
  --text-sm:    0.875rem / 14px  (Secondary text, card descriptions)
  --text-base:  1rem / 16px      (Body text, form inputs)
  --text-lg:    1.125rem / 18px  (Card titles, section subtitles)
  --text-xl:    1.25rem / 20px   (Section headings)
  --text-2xl:   1.5rem / 24px    (Page titles)
  --text-3xl:   1.875rem / 30px  (Hero headings)
  --text-4xl:   2.25rem / 36px   (Big numbers — Total Spend, price)

LINE HEIGHT
  Tight: 1.25 (headings)
  Normal: 1.5 (body)
  Relaxed: 1.75 (long-form descriptions)

FONT WEIGHTS
  Regular: 400 (body text)
  Medium: 500 (labels, emphasis)
  Semi-Bold: 600 (card titles, section heads)
  Bold: 700 (page titles, prices, big numbers)
Spacing System
Based on 4px grid:
  --space-1:   0.25rem / 4px
  --space-2:   0.5rem / 8px
  --space-3:   0.75rem / 12px
  --space-4:   1rem / 16px
  --space-5:   1.25rem / 20px
  --space-6:   1.5rem / 24px
  --space-8:   2rem / 32px
  --space-10:  2.5rem / 40px
  --space-12:  3rem / 48px
  --space-16:  4rem / 64px

LAYOUT
  --max-width:        1280px    (Content max width)
  --sidebar-width:    320px     (Right sidebar on product/search pages)
  --card-gap:         16px      (Gap between product cards in grid)
  --section-gap:      48px      (Gap between homepage sections)
  --page-padding-x:   16px (mobile), 24px (tablet), 48px (desktop)
Border Radius
  --radius-sm:    4px   (Small badges, tags)
  --radius-md:    8px   (Cards, inputs, buttons)
  --radius-lg:    12px  (Large cards, modals)
  --radius-xl:    16px  (Hero sections, feature cards)
  --radius-full:  9999px (Pills, avatar, round badges)
Shadows
  --shadow-sm:    0 1px 2px rgba(0,0,0,0.05)                         (Subtle)
  --shadow-md:    0 4px 6px -1px rgba(0,0,0,0.1)                     (Cards)
  --shadow-lg:    0 10px 15px -3px rgba(0,0,0,0.1)                   (Dropdowns, modals)
  --shadow-card:  0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)  (Product cards)
Component Patterns (Extracted from Screens)
Header / Navbar
Layout: Logo | Browse Categories ▼ | Search bar (centered, prominent) | Post a Review | Login/Welcome | Notification bell
Height: ~64px
Background: White with subtle bottom border
Search bar: Rounded, gray bg (#F1F5F9), with category dropdown prefix ("All Categories ▼")
Logged in: Orange avatar circle with initial + "Welcome, {Name}"
CTA button: "Link orders" / "Sign up" — Orange filled, rounded
Product Card (Homepage & Search)
Structure:
  ┌─────────────────────┐
  │ [Recommended] badge  │  ← Orange/green top-left badge
  │                      │
  │    Product Image     │  ← White bg, centered, ~200px height
  │                      │
  │ ★★★★★ 4.8           │  ← Yellow stars + rating number
  │ (127 reviews)        │  ← Gray text, parenthesized
  │                      │
  │ Product Title (2     │  ← Semi-bold, dark, 2-line clamp
  │ lines max)           │
  │ Brand Name           │  ← Teal/green link text
  │                      │
  │ ₹250  a Best buy     │  ← Bold price + marketplace icon + "Best buy" green text
  │ 🏷️ Selling at fast   │  ← Small gray badge/indicator
  └─────────────────────┘

Card: White bg, subtle border (#E2E8F0), 8px radius, shadow-card on hover
Badge: "Recommended" — Orange bg, white text, top-left overlay
       "Best of Whydud" — Red/orange bg, white text (product page)
Price: Bold, dark, ₹ prefix
"Best buy" next to marketplace icon (Amazon 'a', Flipkart 'F' etc.)
DudScore Display
Two variants seen:

1. Gauge (Product Page):
   Semi-circular gauge dial from Low (red) to High (green)
   Needle pointing to current score
   Color gradient: Red → Yellow → Green
   
2. Percentage Badge (Seller Page):
   Circular badge with percentage number inside
   Teal border, "Seller Trustscore" label below
Price History Chart
Multi-line chart (Recharts style)
X-axis: Months (Jan, Feb, Mar...)
Y-axis: ₹ prices (₹10K, ₹20K, ₹30K, ₹40K)
Lines: Different colors per marketplace (Amazon blue, Flipkart pink/red, Myntra teal)
Time range tabs: "2-3 days" | "Week" | "Month" (pill-style tabs)
Platform filter dropdown: "All Platforms ▼"
Background: White card with border
Marketplace Price Comparison (Product Page)
"Compare all available options" section:
  ┌───────────────────────────┐
  │ [M] Myntra     ₹27,000 > │  ← Green highlight = Current Best
  │     Current Best price    │
  ├───────────────────────────┤
  │ [F] Flipkart   ₹29,000 > │  ← Gray text "12% Higher"
  ├───────────────────────────┤
  │ [A] Amazon      ₹30,500 > │  ← Gray text "19% Higher"
  └───────────────────────────┘
  
Marketplace icons: Small colored squares with letter
Best price: Green background card
Others: White bg, percentage difference shown
Each row is clickable (→ affiliate link)
Category Score Bars (Product Page)
Horizontal bar visualization:
  Style & Design    ● ● ● ● ○  (filled dots in orange/teal gradient)
  Look & Feel       ● ● ● ○ ○
  User Friendly     ● ● ● ● ○
  Value for Money   ● ● ● ○ ○
  
Dots: Small circles, filled = colored, empty = gray
Colors: Gradient from warm (orange) to cool (teal) across the 5 dots
Review Card
  ┌─────────────────────────────────┐
  │ 👤 Akash kumar  1 day ago       │
  │ ★★☆☆☆                          │
  │                                  │
  │ Display stopped after 5 months   │  ← Bold title
  │ I think it's a compact phone... │  ← Regular body text
  │                                  │
  │ 👍 Helpful | ↗ Share | 💬 Comment | ⚠ Report │
  └─────────────────────────────────┘
Rating Distribution (Product Page Sidebar)
Customer rating
★★★★★ 4 out of 5
112 reviews
77% would recommend

5 ████████████████ 52%
4 ████████         12%
3 ██████            8%
2 █                 0%
1 ██████           15%

Horizontal bars, green for 5-star, graduated to red for 1-star
Percentage labels right-aligned
Comparison Table (Comparison Page)
Header: Product images + names + prices + "Best buy" badge
Sub-sections with gray headers:
  - Highlights (Best Overall, Best Value, Best Display)
  - Category Scores (same dot pattern)
  - Ratings (stars + review count + DudScore)
  - Key Specs (with "Best" green badge on winner per row)
  - Detailed Summary (grouped: General, Unique Features, Performance)
  - Quick TCO (at bottom: estimated cost, ₹/year, ₹/month, with 3-year selector)

"Show only differences" checkbox at top
Navigation tabs: Highlights | Comparison Summary | Detailed Comparison | Total cost of ownership
"Best" badge: Green text, used to highlight winner per spec row
Expense Tracker / Dashboard
Top stat cards (4 across):
  Total spend | Orders | Average order value | Top platform
  Big number, small label above, icon left

Tab navigation: Overview | Platforms | Categories | Timeline | Insights

Charts:
  Monthly Spend: Area/line chart with weekly breakdown
  Spend by Platform: Donut chart (Amazon blue, Flipkart teal, Others purple)
  Spend by Category: Horizontal bar chart (Fashion, Electronics, Groceries, Home)

Insight cards at bottom (3 across):
  Icon + bold heading + description
  "Your biggest platform is Amazon" / "Electronics is your top category" / "Friday is your biggest spending day"

Colors: Navy/dark blue (#1E293B) for chart fills, teal for secondary, purple for tertiary
Background: Light gray (#F8FAFC) page bg, white cards
Seller Page
Header card: Avatar | Seller Name + "Verified seller" badge | Stars + rating | Products count | "Seller since X years" | TrustScore gauge
Tab navigation: Seller info | Reviews | Return/Refund policy | Product Catalog
Sidebar: Seller Performance metrics (Avg Resolution Time, Turnaround Time, Response Rate — with green/colored values)
Report/Enquire card in sidebar
Content: Description, Product Categories (pill tags), Customer photos grid, Socials, Contact
Search Results Page
Left: No filter sidebar in this design (may add later — architecture has it)
Center: Product grid (4 columns desktop), "Results for {query}" + "Sort by: Popularity ▼"
Right sidebar: Seller Details card (when browsing a specific store)
  - Seller name, verified badge, rating, description
  - Social links
  - "View seller details" button
  - "View all sellers" expandable
  - Top reviews from seller (horizontal scroll)
  - Related products
Store-scoped search: "✕ This store only" pill in search bar

PART 2: DESIGN BRIEFS FOR MISSING SCREENS
The Figma covers 6 screens. The architecture requires 14+ pages. Here are design briefs for the remaining screens, following the established design language.
Screen: Login Page
Route: /login
Layout: Centered card on light gray background

┌──────────────────────────────────────────┐
│           [Whydud Logo]                  │
│                                          │
│    Welcome back                          │  ← text-2xl, semi-bold
│    Sign in to your account               │  ← text-sm, text-secondary
│                                          │
│    ┌────────────────────────────────┐    │
│    │ Email                          │    │  ← Input with label
│    └────────────────────────────────┘    │
│    ┌────────────────────────────────┐    │
│    │ Password                    👁  │    │  ← Show/hide toggle
│    └────────────────────────────────┘    │
│                                          │
│    □ Remember me      Forgot password?   │
│                                          │
│    ┌────────────────────────────────┐    │
│    │         Sign in                │    │  ← Orange filled button, full width
│    └────────────────────────────────┘    │
│                                          │
│    ────────── or ──────────              │
│                                          │
│    ┌────────────────────────────────┐    │
│    │  [G] Continue with Google      │    │  ← White bg, border, Google icon
│    └────────────────────────────────┘    │
│                                          │
│    Don't have an account? Sign up        │  ← "Sign up" in orange link
└──────────────────────────────────────────┘

Card: White, radius-lg, shadow-lg, max-width 440px
Inputs: radius-md, border, padding 12px, focus ring orange
Screen: Registration (Multi-Step)
Route: /register
Layout: Same centered card, with step indicator

Step 1: Create Account
  Name, Email, Password (strength indicator), Terms checkbox, "Create account" button, Google OAuth

Step 2: Choose @whyd.xyz Email
  ┌────────────────────────────────────────┐
  │ 📧 Get your free @whyd.xyz email       │
  │                                         │
  │ Use this on shopping sites for          │
  │ automatic purchase tracking             │
  │                                         │
  │ ┌──────────────────┐ @whyd.xyz         │
  │ │ ramesh           │                    │  ← Input + fixed suffix
  │ └──────────────────┘                    │
  │ ✅ Available!  (or ❌ Taken + suggestions) │
  │                                         │
  │ [Create email]      Skip for now →      │
  └────────────────────────────────────────┘

Step 3: Onboarding — Register on Shopping Sites
  Marketplace checklist with expand/collapse per site
  Each: Logo + Name + Step-by-step instructions + "I've added it ☑" checkbox
  Progress indicator: "3 of 8 sites set up"
  "I'll do this later" link at bottom

Step indicator: 3 dots at top (●  ○  ○), connected by line, active = orange
Screen: Inbox (@whyd.xyz)
Route: /inbox
Layout: Full-width, three-column (sidebar | email list | reader)

┌──────┬────────────────────────────┬──────────────────────────────┐
│Inbox │ 🔍 Search emails...        │ Subject line (large)         │
│      │                            │ From: auto-confirm@amazon.in │
│📥 All│ ┌────────────────────────┐ │ Date: Feb 22, 2026           │
│📦 Ord│ │ 🛒 Amazon.in           │ │                              │
│🚚 Shi│ │ Your order of OnePlus..│ │ ┌──────────────────────────┐ │
│💰 Ref│ │ 2 hours ago   📦 Order │ │ │ 📦 Order Detected        │ │
│🔄 Sub│ ├────────────────────────┤ │ │ OnePlus Nord 5            │ │
│📢 Pro│ │ 🛒 Flipkart            │ │ │ ₹27,000 on Amazon.in     │ │
│⭐ Sta│ │ Order confirmed #FLP...│ │ │ DudScore: 82 ● Good      │ │
│🗑️ Tra│ │ Yesterday     📦 Order │ │ │ [View in Dashboard]      │ │
│      │ ├────────────────────────┤ │ └──────────────────────────┘ │
│──────│ │ 🛒 Myntra              │ │                              │
│Amazon│ │ Refund processed for...│ │ (Rendered email HTML below   │
│Flipk.│ │ 3 days ago    💰 Refund│ │  with images proxied)       │
│Myntra│ │                        │ │                              │
│      │ │ (more emails...)       │ │                              │
└──────┴────────────────────────────┴──────────────────────────────┘

Mobile: Stacked — folder drawer + email list, tap to open reader full-screen
Colors: Unread = bold text + blue dot. Category badges use semantic colors.
Sidebar folders: Count badges (unread count in each)
Marketplace filter: Below folders, with marketplace logos
Parsed data card: Green border, appears above email body when order/refund detected
Screen: Wishlist
Route: /wishlists
Layout: Dashboard layout (sidebar + content)

┌────────────────────────────────────────────────────────────────┐
│ My Wishlists                              [+ Create Wishlist]  │
│                                                                │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│ │ 📋 Birthday  │ │ 🏠 Home Setup│ │ 💻 Tech      │              │
│ │ 8 items      │ │ 12 items     │ │ 5 items      │              │
│ │ ₹24,500 total│ │ ₹1,12,000   │ │ ₹89,000      │              │
│ │ 3 price drops│ │ 1 price drop │ │ 0 drops      │              │
│ └─────────────┘ └─────────────┘ └─────────────┘              │
│                                                                │
│ ═══════════════════════════════════════════════════════════    │
│                                                                │
│ Birthday Gifts (8 items)                    Total: ₹24,500     │
│                                                                │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ 🖼️ Product Image | Title                  | Added price  │  │
│ │                   | Brand                  | Current: ₹X  │  │
│ │                   | DudScore badge         | ↓ -12% 📉    │  │
│ │                   | Target: ₹1,500 [Edit]  | [Remove]     │  │
│ │                   | Alert: ✅ ON           |              │  │
│ └──────────────────────────────────────────────────────────┘  │
│ │ ... more items ...                                          │
│                                                                │
│ Share wishlist: [🔗 Get share link]                            │
└────────────────────────────────────────────────────────────────┘

Price change indicators: Green ↓ for drops, Red ↑ for increases
Target price: Editable inline
Alert toggle: Switch component
Screen: Deals Page
Route: /deals
Layout: Full width, homepage-style grid

┌────────────────────────────────────────────────────────────────┐
│ 🔥 Blockbuster Deals            Updated 23 min ago  [142 live]│
│                                                                │
│ [Error Pricing] [Lowest Ever] [Massive Discounts] [All]       │ ← Pill tabs, orange active
│                                                                │
│ Category: [All ▼]  Min discount: [50% ────●── 90%]  Sort: [▼] │
│                                                                │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌─────┐│
│ │🔥 Error Price │ │📉 Lowest Ever │ │💰 65% Off     │ │...  ││
│ │               │ │               │ │               │ │     ││
│ │ Product Image │ │ Product Image │ │ Product Image │ │     ││
│ │               │ │               │ │               │ │     ││
│ │ Product Title │ │ Product Title │ │ Product Title │ │     ││
│ │               │ │               │ │               │ │     ││
│ │ ₹499  ₹2,999 │ │ ₹12,999      │ │ ₹1,299       │ │     ││
│ │ -83% ████     │ │ All-time low  │ │ vs ₹3,699    │ │     ││
│ │ 📈 sparkline  │ │ 📈 sparkline  │ │ Genuine ✅    │ │     ││
│ │               │ │               │ │               │ │     ││
│ │ [A] Amazon    │ │ [F] Flipkart  │ │ [M] Myntra    │ │     ││
│ │ Found 23m ago │ │ Found 2h ago  │ │ Found 1h ago  │ │     ││
│ │               │ │               │ │               │ │     ││
│ │ [🛒 Buy Now]  │ │ [🛒 Buy Now]  │ │ [🛒 Buy Now]  │ │     ││
│ └───────────────┘ └───────────────┘ └───────────────┘ └─────┘│
└────────────────────────────────────────────────────────────────┘

Deal type badges: Red "🔥 Error Price", Blue "📉 Lowest Ever", Green "💰 65% Off"
Sparkline: Tiny inline price chart showing the drop
"Found X ago" in gray, creates urgency
Buy Now button: Orange, prominent, full-width inside card
Screen: Rewards
Route: /rewards
Layout: Dashboard layout

┌────────────────────────────────────────────────────────────────┐
│ 🎁 Rewards                                                     │
│                                                                │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ Your Balance: 450 points                  ≈ ₹45 value    │  │
│ │ ████████████████████░░░░░ 550 more for ₹100 gift card    │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                                │
│ ── How to Earn ──                                             │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│ │ ✍️ Review │ │ 📧 Email │ │ 👥 Refer │ │ 🔥 Streak│         │
│ │ +20 pts  │ │ +50 pts  │ │ +30 pts  │ │ +10 pts  │         │
│ │ Write a  │ │ Connect  │ │ Invite a │ │ 7-day    │         │
│ │ review   │ │ @whyd.xyz│ │ friend   │ │ login    │         │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
│                                                                │
│ ── Redeem Gift Cards ──                                       │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│ │ [Amazon] │ │[Flipkart]│ │ [Swiggy] │ │ [Zomato] │         │
│ │ ₹100     │ │ ₹100     │ │ ₹100     │ │ ₹100     │         │
│ │ 1000 pts │ │ 1000 pts │ │ 1000 pts │ │ 1000 pts │         │
│ │ [Redeem] │ │ [Redeem] │ │ [Redeem] │ │ [Redeem] │         │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
│                                                                │
│ ── Points History ──                                          │
│ +20  Review on OnePlus Nord 5          Feb 22, 2026           │
│ +50  Connected @whyd.xyz email         Feb 20, 2026           │
│ -1000 Redeemed Amazon ₹100 gift card  Feb 18, 2026           │
└────────────────────────────────────────────────────────────────┘
Screen: Settings
Route: /settings
Layout: Dashboard with tab navigation

Tabs: Profile | @whyd.xyz Email | Payment Cards | TCO Preferences | Subscription | Data & Privacy

Profile tab:
  Name, email, avatar upload, password change

@whyd.xyz tab:
  Email address display, status badge, stats, marketplace onboarding checklist, deactivate/delete

Payment Cards tab (Card Vault):
  "We never store card numbers" security badge
  List of saved cards with bank logo + variant name + network
  Add card dialog: method type → bank → variant → network → nickname
  Wallets section: Amazon Pay, Paytm etc. with balance
  Memberships: Prime, Plus toggles

TCO Preferences tab:
  City selector (autocomplete)
  Electricity tariff (auto-filled, editable)
  Default ownership years slider
  Default AC hours/day, washer loads/week etc.

Subscription tab:
  Current plan (Free/Premium)
  Premium features list
  Upgrade button → Razorpay
  Cancel subscription

Data & Privacy tab:
  Export my data (JSON download)
  Delete account (danger zone, typed confirmation)
  Connected services (Gmail, @whyd.xyz)
  Disconnect options
Screen: Discussion Thread
Route: /discussions/:id (also embedded on product page)

On product page: Preview cards (3-4 threads, "View all discussions" link)

Full thread page:
┌────────────────────────────────────────────────────────────────┐
│ ← Back to OnePlus Nord 5                                       │
│                                                                │
│ [Question] Does this phone support 5G on Jio?                 │
│ Asked by Ramesh • 3 days ago • 12 replies                      │
│                                                                │
│ I'm considering buying this but I need to know if VoLTE        │
│ and 5G work properly on Jio network. Has anyone tested?        │
│                                                                │
│ ▲ 15 ▼                                                         │
│                                                                │
│ ── Replies ──                                    Sort: Top ▼   │
│                                                                │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ ✅ Accepted Answer                                        │  │
│ │ Akash Kumar • 2 days ago                                  │  │
│ │                                                           │  │
│ │ Yes, tested with Jio 5G in Delhi. Works perfectly.        │  │
│ │ VoLTE also works. Speed test showed 400Mbps download.     │  │
│ │                                                           │  │
│ │ ▲ 24 ▼    💬 Reply                                        │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                                │
│ │ Priya Sharma • 1 day ago                                    │
│ │ Same experience in Mumbai. 5G is fast on Jio.               │
│ │ ▲ 8 ▼    💬 Reply                                           │
│                                                                │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ Write a reply...                                          │  │
│ │                                                           │  │
│ │                                          [Post Reply]     │  │
│ └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘

Thread type badges: [Question] blue, [Experience] purple, [Tip] green, [Alert] red
Accepted answer: Green border + ✅ badge
Vote buttons: ▲ ▼ with count between them (Reddit-style)
Screen: TCO Calculator (Product Page Section)
Embedded on product page, between specs and reviews:

┌────────────────────────────────────────────────────────────────┐
│ 💡 Total Cost of Ownership                                     │
│ See what this AC really costs over time                        │
│                                                                │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ City: [Delhi ▼]     Usage: [──●──── 8 hrs/day]          │   │
│ │ Tariff: [₹8.50/kWh] Years: [──●── 5 years]             │   │
│ │                                              [Calculate] │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                │
│ Total Cost: ₹78,000 over 5 years                              │ ← Big number
│ That's ₹1,300/month to own this product                       │
│                                                                │
│ ┌──────────────────────────────┐ ┌─────────────────────────┐  │
│ │ [Stacked bar chart]          │ │ Category Rank            │  │
│ │ Purchase    ████████ 54%     │ │ #12 of 45 ACs            │  │
│ │ Electricity ██████   33%     │ │ Top 27% cheapest to own  │  │
│ │ Maintenance ██       10%     │ │ ₹4,000 below avg         │  │
│ │ Other       █         3%     │ └─────────────────────────┘  │
│ └──────────────────────────────┘                              │
│                                                                │
│ 💬 "Over 5 years, the Daikin 5-Star Inverter AC will cost     │
│ approximately ₹78,000. Electricity is the biggest ongoing      │
│ expense at 33%. This ranks in the top 27% cheapest to own."   │
│                                                                │
│ [Compare TCO with other ACs →]                                │
└────────────────────────────────────────────────────────────────┘

Note: Comparison page already shows "Quick TCO" at the bottom of the table.
The full version goes deeper with interactive inputs.
Screen: Card Vault Deal Display (Product Page Enhancement)
On product page, inside pricing panel (between marketplace prices and price history):

┌────────────────────────────────────────────────────────────────┐
│ 🏆 Best Deal For Your Cards                                    │
│                                                                │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ Buy on Amazon.in with HDFC Regalia                       │  │
│ │                                                          │  │
│ │ Base price:         ₹27,000                              │  │
│ │ HDFC 10% off:       -₹1,500  (max cap)                  │  │
│ │ Amazon Pay:         -₹100    (max cap)                   │  │
│ │ ───────────────────────────                              │  │
│ │ Effective Price:    ₹25,400  ← Large, green, bold       │  │
│ │                                                          │  │
│ │ 💳 Or: No-cost EMI ₹4,233/mo × 6 months (SBI)          │  │
│ │                                                          │  │
│ │ [🛒 Buy on Amazon.in]                    You save ₹1,600 │  │
│ └──────────────────────────────────────────────────────────┘  │
│                                                                │
│ Other options for your cards:                     [See all ▼]  │
│ • Flipkart + Axis Flipkart: ₹26,149 (save ₹850)             │
│ • Amazon + Amazon Pay ICICI: ₹26,350 (save ₹650)             │
│                                                                │
│ 🔒 We never see your card numbers  [Manage cards →]           │
└────────────────────────────────────────────────────────────────┘

Best deal card: Light green background border, prominent
Savings: Green text, bold
EMI line: Subtle, secondary option
"Other options" collapsed by default, expandable
Security note: Small gray text with lock icon