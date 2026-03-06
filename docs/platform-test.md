Read `PROGRESS.md` first, then `CLAUDE.md`, then `architecture.md`.

Your job is to **audit every feature claimed as "built" or "working"** in PROGRESS.md and verify it actually works. Do NOT build anything new. Do NOT fix anything. Just test and report.

Run every check below. For each item, report one of:
- **PASS** — code exists, compiles/imports cleanly, logic is real (not a stub)
- **PARTIAL** — code exists but incomplete, has TODOs, or has obvious bugs
- **STUB** — function/class exists but body is `pass`, `TODO`, or returns dummy data
- **FAIL** — code is missing, imports break, or doesn't match the spec
- **SKIP** — requires running server/network/external service, can't verify statically

At the end, produce a summary file: `AUDIT-REPORT-{date}.md` in the project root.

---

## PHASE 1: BACKEND MODEL & MIGRATION AUDIT

For each of the 13 Django apps, verify:

```bash
# 1. All models import cleanly
python -c "from apps.accounts.models import *; print('accounts OK')"
python -c "from apps.products.models import *; print('products OK')"
python -c "from apps.pricing.models import *; print('pricing OK')"
python -c "from apps.reviews.models import *; print('reviews OK')"
python -c "from apps.scoring.models import *; print('scoring OK')"
python -c "from apps.email_intel.models import *; print('email_intel OK')"
python -c "from apps.wishlists.models import *; print('wishlists OK')"
python -c "from apps.deals.models import *; print('deals OK')"
python -c "from apps.rewards.models import *; print('rewards OK')"
python -c "from apps.discussions.models import *; print('discussions OK')"
python -c "from apps.tco.models import *; print('tco OK')"
python -c "from apps.search.models import *; print('search OK')"
python -c "from apps.scraping.models import *; print('scraping OK')"

# 2. Check migration count per app
python manage.py showmigrations --list 2>/dev/null | head -100

# 3. Verify 49 model classes exist
python -c "
from django.apps import apps
total = 0
for app_config in apps.get_app_configs():
    if app_config.name.startswith('apps.'):
        models = app_config.get_models()
        count = len(list(models))
        total += count
        print(f'{app_config.label}: {count} models')
print(f'TOTAL: {total} models')
"

# 4. Check TimescaleDB hypertables are defined
grep -rn 'hypertable\|timescale\|create_hypertable' backend/apps/pricing/migrations/ backend/apps/scoring/migrations/
```

**Expected:** 49 models across 13 apps, 27+ migrations, 2 hypertables (PriceSnapshot, DudScoreHistory).

---

## PHASE 2: SERIALIZER & VIEW AUDIT

```bash
# 1. Every app's serializers import cleanly
for app in accounts products pricing reviews scoring email_intel wishlists deals rewards discussions tco search scraping; do
  python -c "from apps.${app}.serializers import *; print('${app} serializers OK')" 2>&1
done

# 2. Every app's views import cleanly
for app in accounts products pricing reviews scoring email_intel wishlists deals rewards discussions tco search scraping; do
  python -c "from apps.${app}.views import *; print('${app} views OK')" 2>&1
done

# 3. Count total URL patterns
python -c "
from django.urls import get_resolver
resolver = get_resolver()
def count_patterns(urlpatterns, prefix=''):
    count = 0
    for p in urlpatterns:
        if hasattr(p, 'url_patterns'):
            count += count_patterns(p.url_patterns, prefix + str(p.pattern))
        else:
            count += 1
    return count
total = count_patterns(resolver.url_patterns)
print(f'Total URL patterns: {total}')
"

# 4. List all API endpoints
python manage.py show_urls 2>/dev/null || python -c "
from django.urls import get_resolver
def list_urls(resolver, prefix=''):
    for p in resolver.url_patterns:
        if hasattr(p, 'url_patterns'):
            list_urls(p, prefix + str(p.pattern))
        else:
            print(f'{prefix}{p.pattern}')
list_urls(get_resolver())
"
```

---

## PHASE 3: API RESPONSE FORMAT AUDIT

Check that views use the standard `{success: true, data: ...}` response format:

```bash
# Check for success_response / error_response usage
echo "=== Views using success_response/error_response ==="
grep -rn "success_response\|error_response" backend/apps/*/views.py | wc -l

echo "=== Views using raw Response() (potential violations) ==="
grep -rn "return Response(" backend/apps/*/views.py | grep -v "success_response\|error_response" | head -20

# Check common/utils.py exists with the helpers
python -c "from common.utils import success_response, error_response; print('Response helpers OK')"
```

---

## PHASE 4: AUTH SYSTEM VERIFICATION

```bash
# 1. Backend auth endpoints exist
python -c "
from apps.accounts.views import RegisterView, LoginView, LogoutView, ProfileView, ChangePasswordView, ResetPasswordView
print('All auth views exist')
"

# 2. OAuth views exist
python -c "
from apps.accounts.views import *
import inspect
members = [m for m in dir() if 'oauth' in m.lower() or 'OAuth' in m]
print(f'OAuth-related: {members}')
"

# 3. Token middleware exists
find backend/ -name "*.py" | xargs grep -l "TokenAuthentication\|token_middleware\|whydud_auth" | head -10

# 4. Frontend auth files exist
echo "=== Frontend Auth Files ==="
ls -la frontend/src/app/\(auth\)/login/page.tsx 2>/dev/null && echo "Login page: EXISTS" || echo "Login page: MISSING"
ls -la frontend/src/app/\(auth\)/register/page.tsx 2>/dev/null && echo "Register page: EXISTS" || echo "Register page: MISSING"
ls -la frontend/src/app/\(auth\)/auth/callback/page.tsx 2>/dev/null && echo "OAuth callback: EXISTS" || echo "OAuth callback: MISSING"
ls -la frontend/src/contexts/auth-context.tsx 2>/dev/null && echo "Auth context: EXISTS" || echo "Auth context: MISSING"
ls -la frontend/src/hooks/useAuth.ts 2>/dev/null && echo "useAuth hook: EXISTS" || echo "useAuth hook: MISSING"
ls -la frontend/src/middleware.ts 2>/dev/null && echo "Middleware: EXISTS" || echo "Middleware: MISSING"

# 5. Verify auth context has login/logout/refresh
grep -n "login\|logout\|refresh\|token" frontend/src/contexts/auth-context.tsx | head -20

# 6. Verify middleware checks cookie
grep -n "whydud_auth\|cookie\|redirect.*login" frontend/src/middleware.ts
```

---

## PHASE 5: FRONTEND PAGES AUDIT

Check every page file exists and has real content (not empty/placeholder):

```bash
echo "=== PUBLIC PAGES ==="
for page in \
  "frontend/src/app/(public)/page.tsx:Homepage" \
  "frontend/src/app/(public)/search/page.tsx:Search" \
  "frontend/src/app/(public)/product/[slug]/page.tsx:Product Detail" \
  "frontend/src/app/(public)/compare/page.tsx:Compare" \
  "frontend/src/app/(public)/deals/page.tsx:Deals" \
  "frontend/src/app/(public)/categories/page.tsx:Categories" \
  "frontend/src/app/(public)/categories/[slug]/page.tsx:Category Detail" \
  "frontend/src/app/(public)/leaderboard/page.tsx:Leaderboard" \
  "frontend/src/app/(public)/seller/[id]/page.tsx:Seller"
do
  FILE=$(echo $page | cut -d: -f1)
  NAME=$(echo $page | cut -d: -f2)
  if [ -f "$FILE" ]; then
    LINES=$(wc -l < "$FILE")
    HAS_API=$(grep -c "Api\|api\.\|fetch\|useEffect" "$FILE" 2>/dev/null || echo 0)
    echo "  $NAME: EXISTS ($LINES lines, API calls: $HAS_API)"
  else
    echo "  $NAME: MISSING"
  fi
done

echo ""
echo "=== DASHBOARD PAGES ==="
for page in \
  "frontend/src/app/(dashboard)/dashboard/page.tsx:Dashboard" \
  "frontend/src/app/(dashboard)/inbox/page.tsx:Inbox" \
  "frontend/src/app/(dashboard)/wishlists/page.tsx:Wishlists" \
  "frontend/src/app/(dashboard)/settings/page.tsx:Settings" \
  "frontend/src/app/(dashboard)/my-reviews/page.tsx:My Reviews" \
  "frontend/src/app/(dashboard)/alerts/page.tsx:Alerts" \
  "frontend/src/app/(dashboard)/purchases/page.tsx:Purchases" \
  "frontend/src/app/(dashboard)/refunds/page.tsx:Refunds" \
  "frontend/src/app/(dashboard)/subscriptions/page.tsx:Subscriptions" \
  "frontend/src/app/(dashboard)/rewards/page.tsx:Rewards" \
  "frontend/src/app/(dashboard)/notifications/page.tsx:Notifications"
do
  FILE=$(echo $page | cut -d: -f1)
  NAME=$(echo $page | cut -d: -f2)
  if [ -f "$FILE" ]; then
    LINES=$(wc -l < "$FILE")
    HAS_API=$(grep -c "Api\|api\.\|fetch\|useEffect" "$FILE" 2>/dev/null || echo 0)
    echo "  $NAME: EXISTS ($LINES lines, API calls: $HAS_API)"
  else
    echo "  $NAME: MISSING"
  fi
done

echo ""
echo "=== AUTH PAGES ==="
for page in \
  "frontend/src/app/(auth)/login/page.tsx:Login" \
  "frontend/src/app/(auth)/register/page.tsx:Register" \
  "frontend/src/app/(auth)/forgot-password/page.tsx:Forgot Password" \
  "frontend/src/app/(auth)/reset-password/page.tsx:Reset Password" \
  "frontend/src/app/(auth)/verify-email/page.tsx:Verify Email"
do
  FILE=$(echo $page | cut -d: -f1)
  NAME=$(echo $page | cut -d: -f2)
  if [ -f "$FILE" ]; then
    LINES=$(wc -l < "$FILE")
    echo "  $NAME: EXISTS ($LINES lines)"
  else
    echo "  $NAME: MISSING"
  fi
done
```

---

## PHASE 6: API CLIENT & TYPE SAFETY AUDIT

```bash
# 1. API client exists and has auth headers
echo "=== API Client ==="
ls -la frontend/src/lib/api/client.ts && echo "EXISTS" || echo "MISSING"
grep -c "Authorization\|Bearer\|token\|whydud_auth" frontend/src/lib/api/client.ts

# 2. Types file exists with key interfaces
echo "=== Types ==="
ls -la frontend/src/lib/api/types.ts && echo "EXISTS" || echo "MISSING"
grep -c "interface\|type " frontend/src/lib/api/types.ts

# 3. Per-domain API modules exist
echo "=== API Modules ==="
for mod in auth products search pricing reviews scoring email wishlists deals rewards discussions tco; do
  FILE=$(find frontend/src/lib/api/ -name "*${mod}*" 2>/dev/null | head -1)
  if [ -n "$FILE" ]; then
    echo "  $mod: $FILE"
  else
    echo "  $mod: NOT FOUND"
  fi
done

# 4. camelCase ↔ snake_case conversion
grep -n "camel\|snake\|transform\|case" frontend/src/lib/api/client.ts | head -10

# 5. TypeScript strict mode check
grep '"strict"' frontend/tsconfig.json
```

---

## PHASE 7: CELERY TASKS AUDIT

Identify which tasks are real vs stubs:

```bash
echo "=== ALL CELERY TASKS ==="
grep -rn "@shared_task\|@app.task\|@celery_app.task" backend/apps/*/tasks.py | while read line; do
  FILE=$(echo "$line" | cut -d: -f1)
  LINENUM=$(echo "$line" | cut -d: -f2)
  # Get task name (next line after decorator)
  TASK_NAME=$(sed -n "$((LINENUM+1))p" "$FILE" | sed 's/def //;s/(.*//;s/ //g')
  # Check if body is stub (pass/TODO/NotImplemented within 5 lines)
  IS_STUB=$(sed -n "$((LINENUM+2)),$((LINENUM+8))p" "$FILE" | grep -c "pass\|TODO\|NotImplemented\|raise NotImplementedError")
  if [ "$IS_STUB" -gt 0 ]; then
    echo "  STUB: $FILE → $TASK_NAME"
  else
    BODY_LINES=$(sed -n "$((LINENUM+2)),$((LINENUM+30))p" "$FILE" | grep -v "^$\|^#\|^ *$" | wc -l)
    echo "  REAL ($BODY_LINES lines): $FILE → $TASK_NAME"
  fi
done

echo ""
echo "=== CELERY BEAT SCHEDULE ==="
grep -A3 "beat_schedule\|crontab\|periodic" backend/whydud/celery.py | head -30

echo ""
echo "=== CELERY QUEUES REFERENCED ==="
grep -rn "queue=" backend/apps/*/tasks.py | sed 's/.*queue=/queue=/' | sort -u
```

---

## PHASE 8: DUDSCORE & FRAUD DETECTION AUDIT

```bash
# 1. DudScore computation is real (not stub)
python -c "
from apps.scoring.tasks import compute_dudscore
import inspect
source = inspect.getsource(compute_dudscore)
lines = source.count('\n')
has_weighted = 'weight' in source.lower()
has_fraud = 'fraud' in source.lower()
has_confidence = 'confidence' in source.lower()
print(f'compute_dudscore: {lines} lines, weighted={has_weighted}, fraud={has_fraud}, confidence={has_confidence}')
"

# 2. DudScore config model has versioning
python -c "
from apps.scoring.models import DudScoreConfig
fields = [f.name for f in DudScoreConfig._meta.get_fields()]
print(f'DudScoreConfig fields: {fields}')
print(f'Has version: {\"version\" in fields}')
"

# 3. Fake review detection is real
python -c "
from apps.reviews.fraud_detection import detect_fake_reviews
import inspect
source = inspect.getsource(detect_fake_reviews)
rules = source.count('Rule')
print(f'detect_fake_reviews: {source.count(chr(10))} lines, {rules} rule references')
"

# 4. Component calculators exist
find backend/apps/scoring/ -name "*.py" | xargs grep -l "def.*calculator\|def.*component\|def.*compute" | head -10
```

---

## PHASE 9: SCRAPING SYSTEM AUDIT

```bash
# 1. Count spiders
echo "=== SPIDER FILES ==="
ls backend/apps/scraping/spiders/*_spider.py 2>/dev/null | wc -l
ls backend/apps/scraping/spiders/*_spider.py 2>/dev/null

# 2. Check which spiders have real logic vs stubs
for spider in backend/apps/scraping/spiders/*_spider.py; do
  NAME=$(basename "$spider" .py)
  LINES=$(wc -l < "$spider")
  HAS_PARSE=$(grep -c "def parse" "$spider")
  HAS_PLAYWRIGHT=$(grep -c "playwright\|PageMethod\|browser" "$spider")
  IS_STUB=$(grep -c "pass$\|TODO\|NotImplemented" "$spider")
  echo "  $NAME: $LINES lines, parse methods=$HAS_PARSE, playwright=$HAS_PLAYWRIGHT, stub indicators=$IS_STUB"
done

# 3. Base spider exists with stealth
grep -n "class BaseWhydudSpider\|stealth\|UA_ROTATION\|user.agent" backend/apps/scraping/spiders/base_spider.py | head -10

# 4. Pipeline chain exists
grep -n "class.*Pipeline" backend/apps/scraping/pipelines.py | head -20

# 5. Scrapy settings
grep "ITEM_PIPELINES\|HTTPERROR_ALLOWED_CODES\|DOWNLOAD_DELAY" backend/apps/scraping/settings.py 2>/dev/null || \
grep "ITEM_PIPELINES\|HTTPERROR_ALLOWED_CODES\|DOWNLOAD_DELAY" backend/whydud/settings/*.py
```

---

## PHASE 10: FRONTEND COMPONENT AUDIT

```bash
# 1. Key components exist
echo "=== LAYOUT COMPONENTS ==="
for comp in header footer sidebar; do
  find frontend/src/components/layout/ -iname "*${comp}*" 2>/dev/null | head -1 | \
    xargs -I{} sh -c 'echo "  {}: $(wc -l < {})"' 2>/dev/null || echo "  $comp: MISSING"
done

echo ""
echo "=== PRODUCT COMPONENTS ==="
for comp in ProductCard PriceChart MarketplacePrices DudScoreBadge ReviewSidebar ShareButton; do
  FOUND=$(find frontend/src/components/ -name "*.tsx" | xargs grep -l "function $comp\|const $comp\|export.*$comp" 2>/dev/null | head -1)
  if [ -n "$FOUND" ]; then
    echo "  $comp: $FOUND ($(wc -l < "$FOUND") lines)"
  else
    echo "  $comp: NOT FOUND"
  fi
done

echo ""
echo "=== DASHBOARD COMPONENTS ==="
for comp in InboxList WishlistCard PriceAlertCard CardVault; do
  FOUND=$(find frontend/src/components/ -name "*.tsx" | xargs grep -l "function $comp\|const $comp\|export.*$comp" 2>/dev/null | head -1)
  if [ -n "$FOUND" ]; then
    echo "  $comp: $FOUND ($(wc -l < "$FOUND") lines)"
  else
    echo "  $comp: NOT FOUND"
  fi
done

# 2. shadcn/ui components installed
echo ""
echo "=== SHADCN UI COMPONENTS ==="
ls frontend/src/components/ui/ 2>/dev/null | wc -l
ls frontend/src/components/ui/ 2>/dev/null | head -20
```

---

## PHASE 11: INFRASTRUCTURE & CONFIG AUDIT

```bash
# 1. Docker Compose services
echo "=== DOCKER COMPOSE SERVICES ==="
grep "^  [a-z].*:" docker/docker-compose.yml 2>/dev/null | sed 's/://' || \
grep "^  [a-z].*:" docker-compose.yml 2>/dev/null | sed 's/://'

# 2. Caddy config
echo ""
echo "=== CADDY CONFIG ==="
find . -name "Caddyfile" -exec head -30 {} \;

# 3. Environment variables template
echo ""
echo "=== ENV TEMPLATE ==="
find . -name ".env.example" -o -name ".env.template" -o -name "env.example" | head -3 | xargs head -40 2>/dev/null

# 4. Requirements files
echo ""
echo "=== REQUIREMENTS ==="
for req in base dev prod scraping; do
  FILE="backend/requirements/${req}.txt"
  if [ -f "$FILE" ]; then
    echo "  $req.txt: $(wc -l < "$FILE") packages"
  else
    echo "  $req.txt: MISSING"
  fi
done

# 5. common/app_settings.py exists with config classes
echo ""
echo "=== APP SETTINGS ==="
python -c "
from common.app_settings import *
import inspect
classes = [name for name, obj in locals().items() if inspect.isclass(obj) and 'Config' in name]
print(f'Config classes: {classes}')
" 2>&1

# 6. common/pagination.py uses cursor
echo ""
echo "=== PAGINATION ==="
grep -n "Cursor\|cursor\|class.*Pagination" backend/common/pagination.py 2>/dev/null | head -5
```

---

## PHASE 12: SECURITY CHECKLIST

```bash
echo "=== SECURITY AUDIT ==="

# 1. Password validation
echo "--- Password ---"
grep -rn "MinimumLengthValidator\|AUTH_PASSWORD_VALIDATORS\|bcrypt\|cost.*12" backend/whydud/settings/ | head -5
grep -rn "password.*min\|password.*length\|password.*8" backend/apps/accounts/ | head -5

# 2. Cookie flags
echo "--- Cookies ---"
grep -rn "httponly\|secure\|samesite\|HTTP_ONLY\|SECURE\|SameSite" backend/ frontend/ | grep -i "cookie\|session" | head -10

# 3. Encryption keys referenced
echo "--- Encryption ---"
grep -rn "EMAIL_ENCRYPTION_KEY\|OAUTH_ENCRYPTION_KEY\|AES.*256\|encrypt\|decrypt" backend/apps/ | head -10

# 4. nh3 sanitization
echo "--- HTML Sanitization ---"
grep -rn "nh3\|sanitize\|bleach" backend/ | head -5

# 5. Rate limiting
echo "--- Rate Limiting ---"
grep -rn "throttle\|rate_limit\|RateLimit\|DEFAULT_THROTTLE" backend/ | head -5

# 6. CORS settings
echo "--- CORS ---"
grep -rn "CORS\|cors\|ALLOWED_ORIGINS" backend/whydud/settings/ | head -5
```

---

## PHASE 13: STUBS & NOT-BUILT VERIFICATION

Verify that things listed as "not built" really aren't built:

```bash
echo "=== CONFIRMING GAPS ==="

# 1. Write a Review form
echo "--- Write a Review ---"
find frontend/src/ -path "*review*" -name "*.tsx" | head -5
grep -rn "WriteReview\|ReviewForm\|review.*form" frontend/src/ | head -5

# 2. Email webhook handler (should be stub)
echo "--- Email Webhook ---"
grep -A15 "webhooks/email\|inbound.*email\|class.*InboundEmail.*View\|def.*inbound" backend/apps/email_intel/views.py 2>/dev/null | head -20

# 3. Notification bell
echo "--- Notification Bell ---"
grep -rn "NotificationBell\|notification.*bell\|unread.*count\|bell.*icon" frontend/src/components/ | head -5

# 4. Forgot password email sending
echo "--- Forgot Password Email ---"
grep -rn "send.*password\|send.*reset\|resend\|Resend" backend/apps/accounts/ | head -10

# 5. Deal detection
echo "--- Deal Detection ---"
cat backend/apps/deals/detection.py 2>/dev/null | head -20

# 6. Reward points engine
echo "--- Rewards Engine ---"
find backend/apps/rewards/ -name "engine.py" -exec head -30 {} \;

# 7. Account deletion / data export
echo "--- DPDP Compliance ---"
grep -rn "delete.*account\|data.*export\|erasure\|DPDP" backend/apps/accounts/ | head -5

# 8. Compare tray (floating)
echo "--- Compare Tray ---"
grep -rn "CompareTray\|compare.*tray\|floating.*compare\|compare.*bar" frontend/src/ | head -5
```

---

## PHASE 14: TYPESCRIPT COMPILATION CHECK

```bash
cd frontend

# 1. Check for TypeScript errors
echo "=== TYPESCRIPT CHECK ==="
npx tsc --noEmit 2>&1 | tail -20

# 2. Count any `any` type usage
echo ""
echo "=== 'any' TYPE USAGE ==="
grep -rn ": any\|<any>\|as any" src/ --include="*.ts" --include="*.tsx" | wc -l
grep -rn ": any\|<any>\|as any" src/ --include="*.ts" --include="*.tsx" | head -15

# 3. Check for raw fetch (should use API client)
echo ""
echo "=== RAW FETCH USAGE (violations) ==="
grep -rn "fetch(" src/app/ src/components/ --include="*.tsx" --include="*.ts" | grep -v "node_modules\|api/client" | head -10
```

---

## PHASE 15: GENERATE AUDIT REPORT

After running all phases above, create a file `AUDIT-REPORT-$(date +%Y-%m-%d).md` in the project root with this structure:

```markdown
# WHYDUD Audit Report — {date}

## Summary
- Total checks run: {N}
- PASS: {N}
- PARTIAL: {N}
- STUB: {N}
- FAIL: {N}
- SKIP: {N}

## Backend Models & Migrations
| App | Models | Migrations | Status |
|-----|--------|------------|--------|
| ... |

## API Endpoints
| Endpoint | View Class | Response Format | Status |
|----------|-----------|-----------------|--------|
| ... |

## Auth System
| Component | Status | Notes |
|-----------|--------|-------|
| ... |

## Frontend Pages
| Page | Route | Lines | API Wired | Status |
|------|-------|-------|-----------|--------|
| ... |

## Celery Tasks
| Task | App | Real/Stub | Queue | Status |
|------|-----|-----------|-------|--------|
| ... |

## DudScore & Fraud Detection
| Component | Status | Notes |
|-----------|--------|-------|
| ... |

## Scraping Spiders
| Spider | Lines | Real/Stub | Playwright | Status |
|--------|-------|-----------|------------|--------|
| ... |

## Security
| Check | Status | Notes |
|-------|--------|-------|
| ... |

## Confirmed Gaps (Not Built)
| Feature | Status | Notes |
|---------|--------|-------|
| ... |

## Recommendations
1. ...
2. ...
```

**IMPORTANT:** Be honest. If something fails, report FAIL. If something is a stub, report STUB. Do NOT assume things work just because PROGRESS.md says they do — verify against actual code.