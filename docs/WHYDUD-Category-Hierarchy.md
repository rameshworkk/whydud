# WHYDUD — Canonical 3-Level Category Hierarchy + Marketplace Mapping

> **Copy-paste this entire prompt into Claude Code.**
> Read PROGRESS.md → CLAUDE.md → architecture.md first.

---

## OBJECTIVE

Replace the current flat category system with a **3-level canonical hierarchy** (Department → Category → Subcategory) and build a **marketplace category mapping** layer so that every scraped product — regardless of how Amazon, Flipkart, Myntra, etc. categorize it — gets assigned to the correct Whydud canonical subcategory.

### Why This Matters
Amazon puts "Indoor Plants" under "Home, Kitchen, Pets" → "Home Decor". Flipkart puts the same thing under "Home Furnishing". Whydud must map both to **Home & Living → Garden & Outdoor → Indoor Plants**. One canonical truth, many marketplace interpretations.

---

## CURRENT STATE (read before coding)

1. **Category model** already exists in `apps/products/models.py` with fields: `id`, `slug`, `name`, `parent_id` (self-FK), `spec_schema` (JSONB), `level` (SMALLINT), `has_tco_model`, `product_count`, `created_at`
2. **~19 categories** exist in DB from seed data — all flat (level=0, parent_id=NULL)
3. **130+ `KEYWORD_CATEGORY_MAP`** entries exist in both `amazon_spider.py` and `flipkart_spider.py` mapping keywords → flat slug
4. **`_resolve_category_from_breadcrumbs()`** in `pipelines.py` auto-creates categories from breadcrumbs
5. **Products** have `category_id` FK pointing to the flat categories
6. **Frontend** has a categories page and category filters in search

---

## TASK BREAKDOWN — DO ALL OF THESE IN ORDER

### PART 1: Add `MarketplaceCategoryMapping` Model

Create a new model in `apps/products/models.py`:

```python
class MarketplaceCategoryMapping(models.Model):
    """
    Maps a marketplace's raw category path to a Whydud canonical category.
    
    Example:
      marketplace: Amazon.in
      marketplace_category_path: "Home, Kitchen, Pets > Home Decor > Artificial Flora"
      marketplace_category_slug: "home-decor/artificial-flora"  
      canonical_category: → Indoor Plants (Whydud subcategory)
    """
    marketplace = models.ForeignKey('Marketplace', on_delete=models.CASCADE, related_name='category_mappings')
    marketplace_category_path = models.CharField(max_length=1000, help_text="Full breadcrumb path as scraped, e.g. 'Electronics > Audio > Headphones'")
    marketplace_category_slug = models.SlugField(max_length=300, help_text="Slugified version of marketplace's leaf category")
    canonical_category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='marketplace_mappings')
    confidence = models.CharField(max_length=20, default='auto', choices=[
        ('manual', 'Manual — admin verified'),
        ('auto', 'Auto — mapped by rules'),
        ('unreviewed', 'Unreviewed — needs admin check'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_category_mappings'
        unique_together = ('marketplace', 'marketplace_category_slug')
        indexes = [
            models.Index(fields=['marketplace', 'marketplace_category_slug']),
        ]

    def __str__(self):
        return f"{self.marketplace.name}: {self.marketplace_category_path} → {self.canonical_category.name}"
```

Also add these fields to the **existing Category model** (if not already present — check first):
- `icon` — `CharField(max_length=50, blank=True, default='')` for a lucide icon name (e.g. `"headphones"`, `"smartphone"`, `"shirt"`)
- `description` — `TextField(blank=True, default='')` for SEO/display
- `is_active` — `BooleanField(default=True)` so we can hide empty categories
- `display_order` — `PositiveIntegerField(default=0)` for controlling sort order in navigation

**DO NOT** change `parent_id`, `level`, or `slug` — they already exist and are correct.

Generate the migration. Use `--name 0005_category_hierarchy_marketplace_mapping` (adjust number to next available).

---

### PART 2: Create the Canonical Category Taxonomy (Seed Command)

Create `backend/apps/products/management/commands/seed_category_hierarchy.py`

This command must:
1. Build the full 3-level tree
2. Use `update_or_create` by slug — safe to run repeatedly
3. Set `level=0` for departments, `level=1` for categories, `level=2` for subcategories
4. Set `parent_id` correctly at each level
5. Reparent any existing flat categories under the right parent (don't delete, don't orphan products)
6. After seeding, print the full tree and count products per category

**THE CANONICAL TAXONOMY** — use exactly this structure. This is India-market focused:

```
Electronics (level=0, slug=electronics)
├── Mobiles & Tablets (level=1, slug=mobiles-tablets)
│   ├── Smartphones (level=2, slug=smartphones)
│   ├── Feature Phones (level=2, slug=feature-phones)
│   ├── Tablets (level=2, slug=tablets)
│   └── Mobile Accessories (level=2, slug=mobile-accessories)
├── Computers & Peripherals (level=1, slug=computers-peripherals)
│   ├── Laptops (level=2, slug=laptops)
│   ├── Desktops (level=2, slug=desktops)
│   ├── Monitors (level=2, slug=monitors)
│   ├── Printers & Scanners (level=2, slug=printers-scanners)
│   ├── Networking (level=2, slug=networking)
│   ├── Computer Accessories (level=2, slug=computer-accessories)
│   └── Storage Devices (level=2, slug=storage-devices)
├── Audio (level=1, slug=audio)
│   ├── Headphones (level=2, slug=headphones)
│   ├── Earphones & Earbuds (level=2, slug=earphones-earbuds)
│   ├── Speakers (level=2, slug=speakers)
│   └── Soundbars (level=2, slug=soundbars)
├── Television & Home Entertainment (level=1, slug=tv-home-entertainment)
│   ├── Televisions (level=2, slug=televisions)
│   ├── Streaming Devices (level=2, slug=streaming-devices)
│   └── Projectors (level=2, slug=projectors)
├── Cameras & Photography (level=1, slug=cameras-photography)
│   ├── DSLR & Mirrorless (level=2, slug=dslr-mirrorless)
│   ├── Action Cameras (level=2, slug=action-cameras)
│   └── Camera Accessories (level=2, slug=camera-accessories)
├── Wearables (level=1, slug=wearables)
│   ├── Smartwatches (level=2, slug=smartwatches)
│   └── Fitness Bands (level=2, slug=fitness-bands)
└── Gaming (level=1, slug=gaming)
    ├── Gaming Consoles (level=2, slug=gaming-consoles)
    ├── Gaming Laptops (level=2, slug=gaming-laptops)
    ├── Gaming Accessories (level=2, slug=gaming-accessories)
    └── Video Games (level=2, slug=video-games)

Home & Living (level=0, slug=home-living)
├── Kitchen (level=1, slug=kitchen)
│   ├── Cookware (level=2, slug=cookware)
│   ├── Kitchen Appliances (level=2, slug=kitchen-appliances)
│   ├── Kitchen Storage (level=2, slug=kitchen-storage)
│   ├── Kitchen Tools (level=2, slug=kitchen-tools)
│   └── Dinnerware (level=2, slug=dinnerware)
├── Home Appliances (level=1, slug=home-appliances)
│   ├── Air Conditioners (level=2, slug=air-conditioners)
│   ├── Refrigerators (level=2, slug=refrigerators)
│   ├── Washing Machines (level=2, slug=washing-machines)
│   ├── Water Purifiers (level=2, slug=water-purifiers)
│   ├── Air Purifiers (level=2, slug=air-purifiers)
│   ├── Vacuum Cleaners (level=2, slug=vacuum-cleaners)
│   ├── Fans & Coolers (level=2, slug=fans-coolers)
│   ├── Geysers & Heaters (level=2, slug=geysers-heaters)
│   └── Irons & Steamers (level=2, slug=irons-steamers)
├── Furniture (level=1, slug=furniture)
│   ├── Living Room Furniture (level=2, slug=living-room-furniture)
│   ├── Bedroom Furniture (level=2, slug=bedroom-furniture)
│   ├── Office Furniture (level=2, slug=office-furniture)
│   └── Storage Furniture (level=2, slug=storage-furniture)
├── Home Decor (level=1, slug=home-decor)
│   ├── Lighting (level=2, slug=lighting)
│   ├── Clocks (level=2, slug=clocks)
│   ├── Wall Art (level=2, slug=wall-art)
│   └── Showpieces (level=2, slug=showpieces)
├── Garden & Outdoor (level=1, slug=garden-outdoor)
│   ├── Indoor Plants (level=2, slug=indoor-plants)
│   ├── Pots & Planters (level=2, slug=pots-planters)
│   ├── Garden Tools (level=2, slug=garden-tools)
│   └── Outdoor Furniture (level=2, slug=outdoor-furniture)
└── Bedding & Bath (level=1, slug=bedding-bath)
    ├── Bedsheets (level=2, slug=bedsheets)
    ├── Towels (level=2, slug=towels)
    ├── Pillows & Cushions (level=2, slug=pillows-cushions)
    └── Bathroom Accessories (level=2, slug=bathroom-accessories)

Appliances (level=0, slug=appliances)
├── Personal Care Appliances (level=1, slug=personal-care-appliances)
│   ├── Trimmers & Shavers (level=2, slug=trimmers-shavers)
│   ├── Hair Dryers & Stylers (level=2, slug=hair-dryers-stylers)
│   └── Electric Toothbrushes (level=2, slug=electric-toothbrushes)
└── Small Appliances (level=1, slug=small-appliances)
    ├── Mixer Grinders (level=2, slug=mixer-grinders)
    ├── Induction Cooktops (level=2, slug=induction-cooktops)
    ├── Electric Kettles (level=2, slug=electric-kettles)
    ├── Sandwich Makers & Grills (level=2, slug=sandwich-makers-grills)
    ├── Microwave Ovens (level=2, slug=microwave-ovens)
    └── OTGs (level=2, slug=otgs)

Fashion (level=0, slug=fashion)
├── Men's Fashion (level=1, slug=mens-fashion)
│   ├── Men's T-Shirts (level=2, slug=mens-tshirts)
│   ├── Men's Shirts (level=2, slug=mens-shirts)
│   ├── Men's Jeans & Trousers (level=2, slug=mens-jeans-trousers)
│   ├── Men's Shoes (level=2, slug=mens-shoes)
│   ├── Men's Watches (level=2, slug=mens-watches)
│   └── Men's Accessories (level=2, slug=mens-accessories)
├── Women's Fashion (level=1, slug=womens-fashion)
│   ├── Women's Ethnic Wear (level=2, slug=womens-ethnic-wear)
│   ├── Women's Western Wear (level=2, slug=womens-western-wear)
│   ├── Women's Shoes (level=2, slug=womens-shoes)
│   ├── Women's Watches (level=2, slug=womens-watches)
│   ├── Women's Handbags (level=2, slug=womens-handbags)
│   └── Women's Jewellery (level=2, slug=womens-jewellery)
├── Kids' Fashion (level=1, slug=kids-fashion)
│   ├── Boys' Clothing (level=2, slug=boys-clothing)
│   ├── Girls' Clothing (level=2, slug=girls-clothing)
│   └── Kids' Shoes (level=2, slug=kids-shoes)
└── Bags & Luggage (level=1, slug=bags-luggage)
    ├── Backpacks (level=2, slug=backpacks)
    ├── Suitcases (level=2, slug=suitcases)
    └── Wallets (level=2, slug=wallets)

Beauty & Personal Care (level=0, slug=beauty-personal-care)
├── Skincare (level=1, slug=skincare)
│   ├── Face Care (level=2, slug=face-care)
│   ├── Body Care (level=2, slug=body-care)
│   └── Sunscreen (level=2, slug=sunscreen)
├── Haircare (level=1, slug=haircare)
│   ├── Shampoo & Conditioner (level=2, slug=shampoo-conditioner)
│   ├── Hair Oil (level=2, slug=hair-oil)
│   └── Hair Styling (level=2, slug=hair-styling)
├── Makeup (level=1, slug=makeup)
│   ├── Lipstick & Lip Care (level=2, slug=lipstick-lip-care)
│   ├── Foundation & Face (level=2, slug=foundation-face)
│   └── Eye Makeup (level=2, slug=eye-makeup)
└── Fragrances (level=1, slug=fragrances)
    ├── Perfumes (level=2, slug=perfumes)
    └── Deodorants (level=2, slug=deodorants)

Health & Wellness (level=0, slug=health-wellness)
├── Nutrition & Supplements (level=1, slug=nutrition-supplements)
│   ├── Protein & Fitness (level=2, slug=protein-fitness)
│   ├── Vitamins & Minerals (level=2, slug=vitamins-minerals)
│   └── Ayurveda (level=2, slug=ayurveda)
└── Medical Devices (level=1, slug=medical-devices)
    ├── BP Monitors (level=2, slug=bp-monitors)
    ├── Glucometers (level=2, slug=glucometers)
    └── Oximeters (level=2, slug=oximeters)

Sports & Fitness (level=0, slug=sports-fitness)
├── Exercise & Fitness (level=1, slug=exercise-fitness)
│   ├── Treadmills & Cycles (level=2, slug=treadmills-cycles)
│   ├── Yoga & Accessories (level=2, slug=yoga-accessories)
│   └── Dumbbells & Weights (level=2, slug=dumbbells-weights)
└── Sports Equipment (level=1, slug=sports-equipment)
    ├── Cricket (level=2, slug=cricket)
    ├── Badminton (level=2, slug=badminton)
    └── Football (level=2, slug=football)

Books & Stationery (level=0, slug=books-stationery)
├── Books (level=1, slug=books)
│   ├── Fiction (level=2, slug=fiction)
│   ├── Non-Fiction (level=2, slug=non-fiction)
│   ├── Academic & Competitive (level=2, slug=academic-competitive)
│   └── Children's Books (level=2, slug=childrens-books)
└── Stationery & Office (level=1, slug=stationery-office)
    ├── Writing Instruments (level=2, slug=writing-instruments)
    └── Office Supplies (level=2, slug=office-supplies)

Baby & Kids (level=0, slug=baby-kids)
├── Baby Care (level=1, slug=baby-care)
│   ├── Diapers & Wipes (level=2, slug=diapers-wipes)
│   ├── Baby Food & Formula (level=2, slug=baby-food-formula)
│   └── Baby Bathing (level=2, slug=baby-bathing)
├── Toys & Games (level=1, slug=toys-games)
│   ├── Educational Toys (level=2, slug=educational-toys)
│   ├── Action Figures (level=2, slug=action-figures)
│   └── Board Games (level=2, slug=board-games)
└── Baby Gear (level=1, slug=baby-gear)
    ├── Strollers (level=2, slug=strollers)
    └── Car Seats (level=2, slug=car-seats)

Automotive (level=0, slug=automotive)
├── Car Accessories (level=1, slug=car-accessories)
│   ├── Car Electronics (level=2, slug=car-electronics)
│   └── Car Care (level=2, slug=car-care)
└── Bike Accessories (level=1, slug=bike-accessories)
    ├── Helmets (level=2, slug=helmets)
    └── Bike Care (level=2, slug=bike-care)

Pet Supplies (level=0, slug=pet-supplies)
├── Dog Supplies (level=1, slug=dog-supplies)
│   ├── Dog Food (level=2, slug=dog-food)
│   └── Dog Accessories (level=2, slug=dog-accessories)
└── Cat Supplies (level=1, slug=cat-supplies)
    ├── Cat Food (level=2, slug=cat-food)
    └── Cat Accessories (level=2, slug=cat-accessories)

Musical Instruments (level=0, slug=musical-instruments)
├── Guitars (level=1, slug=guitars)
│   ├── Acoustic Guitars (level=2, slug=acoustic-guitars)
│   └── Electric Guitars (level=2, slug=electric-guitars)
└── Keyboards & Pianos (level=1, slug=keyboards-pianos)
    ├── Keyboards (level=2, slug=keyboards-music)
    └── Digital Pianos (level=2, slug=digital-pianos)
```

**IMPORTANT — handling existing flat categories:**

The DB already has ~19 categories with level=0 and no parent. The seed command must:
1. Check if each slug already exists
2. If it exists at level=0 and should be at level=2 (e.g. `smartphones` currently exists as a flat root) — UPDATE its `parent_id` and `level` to correct values. DO NOT create a duplicate.
3. If a slug exists and has products attached — keep it, just reparent. Never orphan products.
4. Run `Category.objects.filter(parent__isnull=True, level=0)` at the end and print any categories that weren't placed in the hierarchy — these are orphans from auto-creation that need manual mapping later.

After building the tree, recalculate `product_count` on every category:
```python
from django.db.models import Count, Q

# Leaf categories: direct product count
for cat in Category.objects.filter(level=2):
    cat.product_count = cat.products.filter(status='active').count()
    cat.save(update_fields=['product_count'])

# Mid-level: sum of children
for cat in Category.objects.filter(level=1):
    cat.product_count = sum(c.product_count for c in cat.children.all())
    cat.save(update_fields=['product_count'])

# Departments: sum of children
for cat in Category.objects.filter(level=0):
    cat.product_count = sum(c.product_count for c in cat.children.all())
    cat.save(update_fields=['product_count'])
```

---

### PART 3: Build the Marketplace Category Mapping Engine

Create `backend/apps/products/category_mapper.py`:

```python
"""
Canonical category mapper.

Maps marketplace-specific category paths/breadcrumbs to Whydud's canonical 
3-level hierarchy. Uses a 4-step resolution:

  1. Exact mapping lookup (MarketplaceCategoryMapping table)
  2. Keyword-based matching (CANONICAL_KEYWORD_MAP) 
  3. Breadcrumb walk (deepest-first matching against known slugs)
  4. Fallback → "Uncategorized" + create unreviewed MarketplaceCategoryMapping

All products MUST end up in a level=2 subcategory. Never assign to level=0 or level=1.
"""
```

The mapper must implement:

```python
def resolve_canonical_category(
    marketplace_slug: str,
    breadcrumbs: list[str] | None,
    title: str,
    raw_category: str | None = None,
) -> Category:
    """
    Resolve a scraped product to its canonical Whydud subcategory (level=2).
    
    Args:
        marketplace_slug: e.g. "amazon-in", "flipkart"
        breadcrumbs: e.g. ["Electronics", "Headphones, Earbuds & Accessories", "Headphones"]
        title: product title for keyword extraction
        raw_category: optional marketplace category string from JSON-LD
        
    Returns:
        Category instance (always level=2)
    """
```

**Step 1 — Exact mapping lookup:**
Build the breadcrumb path string (e.g. `"Electronics > Headphones, Earbuds & Accessories > Headphones"`), slugify the leaf, and look up `MarketplaceCategoryMapping.objects.filter(marketplace__slug=marketplace_slug, marketplace_category_slug=leaf_slug).first()`. If found and `canonical_category.level == 2`, return it.

**Step 2 — Keyword-based matching:**
Build a single `CANONICAL_KEYWORD_MAP` dict that maps known keywords/phrases to canonical subcategory slugs. This replaces the per-spider `KEYWORD_CATEGORY_MAP` dicts. Examples:

```python
CANONICAL_KEYWORD_MAP: dict[str, str] = {
    # Audio
    "headphones": "headphones",
    "headphone": "headphones",
    "over-ear": "headphones",
    "on-ear": "headphones",
    "earphones": "earphones-earbuds",
    "earbuds": "earphones-earbuds",
    "tws": "earphones-earbuds",
    "true wireless": "earphones-earbuds",
    "neckband": "earphones-earbuds",
    "bluetooth speaker": "speakers",
    "portable speaker": "speakers",
    "soundbar": "soundbars",
    "home theatre": "soundbars",
    
    # Mobiles
    "smartphone": "smartphones",
    "mobile phone": "smartphones",
    "iphone": "smartphones",
    "galaxy": "smartphones",
    "pixel": "smartphones",
    "tablet": "tablets",
    "ipad": "tablets",
    
    # Computers
    "laptop": "laptops",
    "notebook": "laptops",
    "macbook": "laptops",
    "gaming laptop": "gaming-laptops",
    "monitor": "monitors",
    "printer": "printers-scanners",
    
    # Home appliances
    "air conditioner": "air-conditioners",
    "split ac": "air-conditioners",
    "window ac": "air-conditioners",
    "refrigerator": "refrigerators",
    "fridge": "refrigerators",
    "washing machine": "washing-machines",
    "water purifier": "water-purifiers",
    "air purifier": "air-purifiers",
    "vacuum cleaner": "vacuum-cleaners",
    
    # Indoor plants (the example from your requirement)
    "indoor plant": "indoor-plants",
    "indoor plants": "indoor-plants",
    "artificial plant": "indoor-plants",
    "money plant": "indoor-plants",
    "succulent": "indoor-plants",
    
    # ... extend this to cover ALL 130+ keywords currently in spider files
    # Claude Code: read the KEYWORD_CATEGORY_MAP from both amazon_spider.py 
    # and flipkart_spider.py and convert ALL entries to canonical subcategory slugs
}
```

Search breadcrumbs + title against this map. Match longest phrase first (multi-word before single-word). Return the canonical subcategory.

**Step 3 — Breadcrumb walk:**
Walk breadcrumbs from deepest to shallowest. Slugify each breadcrumb segment. Check if `Category.objects.filter(slug=slugified_segment, level=2).exists()`. If found, return it.

**Step 4 — Fallback:**
If no match found:
- Create a `MarketplaceCategoryMapping` with `confidence='unreviewed'` pointing to a special **"Uncategorized"** subcategory (create this under a hidden "Other" department if it doesn't exist)
- Log a warning: `logger.warning(f"Unmapped category: {marketplace_slug} | {breadcrumbs} | {title}")`
- Return the Uncategorized category

**ALSO:** When a mapping IS found via steps 2 or 3, auto-create a `MarketplaceCategoryMapping` record with `confidence='auto'` so future products with the same marketplace breadcrumb resolve via step 1 (fast path).

---

### PART 4: Update the Scraping Pipeline

Modify `backend/apps/scraping/pipelines.py`:

1. **Replace** the existing `_resolve_category_from_breadcrumbs()` method in `ProductPipeline` with a call to the new `resolve_canonical_category()` function.

2. Pass all available data:
```python
from apps.products.category_mapper import resolve_canonical_category

# In ProductPipeline.process_item():
category = resolve_canonical_category(
    marketplace_slug=item.get('marketplace_slug', ''),
    breadcrumbs=item.get('breadcrumbs', []),
    title=item.get('title', ''),
    raw_category=item.get('category', ''),
)
```

3. **Remove** the `KEYWORD_CATEGORY_MAP` dicts from `amazon_spider.py` and `flipkart_spider.py`. These spiders should no longer do category resolution — the pipeline handles it centrally. The spiders should still pass `breadcrumbs` and `category` fields in the item.

4. **Keep** the seed URL lists and per-category page limits in spiders — those are unrelated to category resolution.

---

### PART 5: Update Serializers & API

**`apps/products/serializers.py`:**

Add/update a `CategorySerializer` that returns the hierarchy:

```python
class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    breadcrumb = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'slug', 'name', 'level', 'icon', 'description',
                  'parent', 'product_count', 'children_count', 'breadcrumb', 'has_tco_model']

    def get_parent(self, obj):
        if obj.parent:
            return {'id': obj.parent.id, 'slug': obj.parent.slug, 'name': obj.parent.name}
        return None

    def get_children_count(self, obj):
        return obj.children.filter(is_active=True).count() if hasattr(obj, 'children') else 0

    def get_breadcrumb(self, obj):
        """Returns ['Electronics', 'Audio', 'Headphones'] for a level-2 category."""
        parts = []
        current = obj
        while current:
            parts.append({'slug': current.slug, 'name': current.name})
            current = current.parent
        return list(reversed(parts))
```

**Add a `CategoryTreeSerializer`** for the mega-nav/browse page:

```python
class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'slug', 'name', 'icon', 'product_count']

class CategoryWithChildrenSerializer(serializers.ModelSerializer):
    subcategories = SubcategorySerializer(source='children', many=True)

    class Meta:
        model = Category
        fields = ['id', 'slug', 'name', 'icon', 'product_count', 'subcategories']

class DepartmentTreeSerializer(serializers.ModelSerializer):
    categories = CategoryWithChildrenSerializer(source='children', many=True)

    class Meta:
        model = Category
        fields = ['id', 'slug', 'name', 'icon', 'product_count', 'categories']
```

**`apps/products/views.py`:**

Add/update a category tree endpoint:

```python
class CategoryTreeView(generics.ListAPIView):
    """GET /api/v1/categories/tree/ — returns full 3-level hierarchy"""
    serializer_class = DepartmentTreeSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Category.objects.filter(
            level=0, is_active=True
        ).prefetch_related(
            Prefetch('children', queryset=Category.objects.filter(is_active=True).prefetch_related(
                Prefetch('children', queryset=Category.objects.filter(is_active=True))
            ))
        ).order_by('display_order', 'name')
```

Update existing category list view to support filtering by level:
```python
# GET /api/v1/categories/?level=0  → departments only
# GET /api/v1/categories/?level=2  → subcategories only
# GET /api/v1/categories/?parent=electronics  → children of electronics
```

**Update `urls.py`** to include the tree endpoint.

---

### PART 6: Update Admin

In `apps/products/admin.py`:

1. **CategoryAdmin** — show hierarchy:
   - `list_display`: `name`, `parent_display`, `level`, `slug`, `product_count`, `is_active`, `display_order`
   - `list_filter`: `level`, `is_active`, `parent` (for level=1 and level=2)
   - `list_editable`: `display_order`, `is_active`
   - `parent_display`: shows "Department → Category" breadcrumb
   - Ordering: `level`, `parent__name`, `display_order`, `name`

2. **MarketplaceCategoryMappingAdmin**:
   - `list_display`: `marketplace`, `marketplace_category_path`, `canonical_category`, `confidence`, `updated_at`
   - `list_filter`: `marketplace`, `confidence`
   - `search_fields`: `marketplace_category_path`, `canonical_category__name`
   - `list_editable`: `canonical_category`, `confidence`
   - Custom action: "Mark as reviewed" → set `confidence='manual'`

---

### PART 7: Update Frontend

**1. Update `frontend/src/lib/api/types.ts`:**
Add the hierarchy types:

```typescript
interface Category {
  id: number;
  slug: string;
  name: string;
  level: number;
  icon: string;
  description: string;
  parent: { id: number; slug: string; name: string } | null;
  productCount: number;
  childrenCount: number;
  breadcrumb: { slug: string; name: string }[];
  hasTcoModel: boolean;
}

interface Department extends Category {
  categories: CategoryWithChildren[];
}

interface CategoryWithChildren extends Category {
  subcategories: Category[];
}
```

**2. Update the categories API module** to add `getTree()`:
```typescript
// GET /api/v1/categories/tree/
getTree(): Promise<Department[]>
```

**3. Update the Categories page** (`frontend/src/app/(public)/categories/page.tsx`):
- Fetch from `/api/v1/categories/tree/`
- Display as collapsible department → category → subcategory grid
- Each subcategory links to `/categories/{subcategory-slug}`
- Show product count badges
- Mobile: accordion-style departments

**4. Update the Category detail page** (`frontend/src/app/(public)/categories/[slug]/page.tsx`):
- Add breadcrumb navigation: Home → Department → Category → Subcategory
- If visiting a department or mid-level category, show its children as cards
- If visiting a subcategory (level=2), show product grid as before

**5. Update the search filter sidebar** — CategoryFilter should show the tree structure, not a flat list.

**6. Update the Header mega-nav** (if it has a categories dropdown) to use the 3-level tree.

---

### PART 8: Update Meilisearch Index

When indexing products to Meilisearch, include the full category hierarchy:

```python
# In the Meilisearch sync task/command, for each product:
{
    "category_slug": product.category.slug,                    # "headphones"
    "category_name": product.category.name,                    # "Headphones"
    "category_parent_slug": product.category.parent.slug,      # "audio"
    "category_parent_name": product.category.parent.name,      # "Audio"  
    "category_department_slug": grandparent.slug,              # "electronics"
    "category_department_name": grandparent.name,              # "Electronics"
    "category_breadcrumb": "Electronics > Audio > Headphones",  # For display
}
```

Make `category_department_slug`, `category_parent_slug`, and `category_slug` all filterable attributes in Meilisearch settings.

---

### PART 9: Run It All

After building everything:

```bash
# 1. Generate and apply migration
python manage.py makemigrations products
python manage.py migrate

# 2. Seed the canonical hierarchy
python manage.py seed_category_hierarchy

# 3. Print the tree to verify
python manage.py shell -c "
from apps.products.models import Category
for dept in Category.objects.filter(level=0).order_by('display_order', 'name'):
    print(f'{dept.name} ({dept.product_count} products)')
    for cat in dept.children.order_by('display_order', 'name'):
        print(f'  ├── {cat.name} ({cat.product_count})')
        for sub in cat.children.order_by('display_order', 'name'):
            print(f'  │   ├── {sub.name} ({sub.product_count})')
"

# 4. Check for orphan categories (flat ones that weren't reparented)
python manage.py shell -c "
from apps.products.models import Category
orphans = Category.objects.filter(parent__isnull=True, level=0).exclude(
    slug__in=[...list of department slugs...]
)
for o in orphans:
    print(f'ORPHAN: {o.slug} ({o.name}) — {o.products.count()} products')
"

# 5. Resync Meilisearch with new category fields
python manage.py sync_meilisearch

# 6. Run TypeScript check
cd frontend && npx tsc --noEmit
```

---

## FILES TO CREATE
- `backend/apps/products/category_mapper.py` (NEW)
- `backend/apps/products/management/commands/seed_category_hierarchy.py` (NEW)
- `backend/apps/products/migrations/XXXX_category_hierarchy_marketplace_mapping.py` (NEW — auto-generated)

## FILES TO MODIFY
- `backend/apps/products/models.py` — add MarketplaceCategoryMapping, add new fields to Category
- `backend/apps/products/serializers.py` — add hierarchy serializers
- `backend/apps/products/views.py` — add CategoryTreeView
- `backend/apps/products/urls.py` — add /tree/ endpoint
- `backend/apps/products/admin.py` — update CategoryAdmin, add MarketplaceCategoryMappingAdmin
- `backend/apps/scraping/pipelines.py` — replace category resolution with canonical mapper
- `backend/apps/scraping/spiders/amazon_spider.py` — remove KEYWORD_CATEGORY_MAP
- `backend/apps/scraping/spiders/flipkart_spider.py` — remove KEYWORD_CATEGORY_MAP
- `backend/apps/search/` — update Meilisearch sync to include hierarchy fields
- `frontend/src/lib/api/types.ts` — add Category hierarchy types
- `frontend/src/lib/api/` — update categories API module
- `frontend/src/app/(public)/categories/page.tsx` — use tree
- `frontend/src/app/(public)/categories/[slug]/page.tsx` — add breadcrumbs, hierarchy browsing
- `frontend/src/components/search/` — update CategoryFilter

## FILES TO NOT TOUCH
- Database schema for `categories` table (parent_id, level already exist)
- Spider seed URLs and page limits
- Product model (category_id FK stays the same)
- DudScore, pricing, reviews — unrelated

## UPDATE PROGRESS.md
After completing all parts, add this entry:
```
### {date} — Canonical 3-Level Category Hierarchy
- Converted flat 19-category system to 3-level hierarchy: {N} departments, {N} categories, {N} subcategories
- Created MarketplaceCategoryMapping model for marketplace→canonical resolution
- Built category_mapper.py with 4-step resolution: exact lookup → keyword → breadcrumb walk → fallback
- Migrated KEYWORD_CATEGORY_MAP from individual spiders to centralized CANONICAL_KEYWORD_MAP
- Updated scraping pipeline to use canonical mapper
- Added /api/v1/categories/tree/ endpoint
- Updated frontend categories page with hierarchy browsing
- Updated Meilisearch index with department/category/subcategory fields
- Reparented {N} existing flat categories, {N} orphans flagged for review
```
