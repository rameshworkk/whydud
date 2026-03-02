# WHYDUD — Multi-Domain Email Architecture

**Domains:**
- whyd.in (India-focused, professional)
- whyd.click (action-oriented, techy)
- whyd.shop (shopping-focused, descriptive)
- whydud.com (corporate only — NOT for user emails)

---

## HOW IT WORKS

```
All 3 domains → Same Cloudflare Account → Same Email Worker → Same Django Webhook → Same Inbox

Amazon sends to ramesh@whyd.in      ─┐
Flipkart sends to ramesh@whyd.click  ├──→ Cloudflare Email Worker → Django → User's Inbox
Myntra sends to ramesh@whyd.shop    ─┘

The user picks ONE email during registration. That's their shopping email.
All 3 domains land in the same pipeline. No difference in processing.
```

---

## DOMAIN DNS SETUP (All 3 Identical)

### whyd.in
```
MX    10  route1.mx.cloudflare.net
MX    20  route2.mx.cloudflare.net
TXT       "v=spf1 include:_spf.mx.cloudflare.net ~all"
TXT       _dmarc  "v=DMARC1; p=reject; rua=mailto:dmarc@whydud.com"
```

### whyd.click
```
MX    10  route1.mx.cloudflare.net
MX    20  route2.mx.cloudflare.net
TXT       "v=spf1 include:_spf.mx.cloudflare.net ~all"
TXT       _dmarc  "v=DMARC1; p=reject; rua=mailto:dmarc@whydud.com"
```

### whyd.shop
```
MX    10  route1.mx.cloudflare.net
MX    20  route2.mx.cloudflare.net
TXT       "v=spf1 include:_spf.mx.cloudflare.net ~all"
TXT       _dmarc  "v=DMARC1; p=reject; rua=mailto:dmarc@whydud.com"
```

### Cloudflare Email Routing Rules
```
For each domain, create ONE catch-all rule:

whyd.in:    *@whyd.in    → Email Worker "whydud-email-handler"
whyd.click: *@whyd.click → Email Worker "whydud-email-handler"
whyd.shop:  *@whyd.shop  → Email Worker "whydud-email-handler"

Same worker handles all 3 domains. It extracts the full recipient
address (including domain) and sends to Django.
```

---

## CLOUDFLARE EMAIL WORKER (Single Worker, All Domains)

```javascript
// whydud-email-handler — deployed once, handles all 3 domains
export default {
  async email(message, env, ctx) {
    const recipient = message.to;           // "ramesh@whyd.in"
    const sender = message.from;            // "auto-confirm@amazon.in"
    const subject = message.headers.get("subject") || "";
    
    // Read raw email
    const rawEmail = await new Response(message.raw).arrayBuffer();
    const base64Body = btoa(String.fromCharCode(...new Uint8Array(rawEmail)));
    
    // Send to Django webhook
    const response = await fetch(env.WEBHOOK_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Webhook-Secret": env.WEBHOOK_SECRET,
      },
      body: JSON.stringify({
        recipient: recipient,        // Full address including domain
        sender: sender,
        subject: subject,
        raw_email: base64Body,
        received_at: new Date().toISOString(),
      }),
    });
    
    if (!response.ok) {
      // If Django is down, forward to dead letter address
      await message.forward(env.DEAD_LETTER_EMAIL);
    }
  },
};
```

---

## DATABASE SCHEMA CHANGES

### Updated WhydudEmail Model

```python
class WhydudEmail(models.Model):
    """
    User's assigned shopping email address.
    One user gets ONE email across any of the 3 domains.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.OneToOneField('accounts.Account', on_delete=models.CASCADE)
    
    username = models.CharField(max_length=30)  # "ramesh" or "ramesh.kumar"
    domain = models.CharField(
        max_length=20,
        choices=[
            ('whyd.in', 'whyd.in'),
            ('whyd.click', 'whyd.click'),
            ('whyd.shop', 'whyd.shop'),
        ],
        default='whyd.in'
    )
    
    is_active = models.BooleanField(default=True)
    total_emails_received = models.IntegerField(default=0)
    last_email_received_at = models.DateTimeField(null=True, blank=True)
    onboarding_complete = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users"."whydud_emails'
        constraints = [
            # Username must be unique WITHIN a domain
            # ramesh@whyd.in and ramesh@whyd.shop are DIFFERENT addresses
            models.UniqueConstraint(
                fields=['username', 'domain'],
                name='unique_email_per_domain'
            ),
        ]
    
    @property
    def email_address(self) -> str:
        return f"{self.username}@{self.domain}"
    
    def __str__(self):
        return self.email_address
```

### Availability Check Logic

```python
def check_username_availability(username: str, domain: str) -> dict:
    """
    Check if username@domain is available.
    
    Returns:
    {
        "available": bool,
        "reason": str or None,     # "taken", "reserved", "invalid"
        "suggestions": list[dict]  # [{"username": "...", "domain": "..."}]
    }
    """
    # Validate username format
    if not re.match(r'^[a-z0-9][a-z0-9._-]{1,28}[a-z0-9]$', username):
        return {
            "available": False,
            "reason": "invalid",
            "message": "Username must be 3-30 characters, lowercase letters, numbers, dots, hyphens.",
            "suggestions": generate_suggestions(username, domain)
        }
    
    # Check reserved usernames (same list applies across all domains)
    if ReservedUsername.objects.filter(username=username.lower()).exists():
        return {
            "available": False,
            "reason": "reserved",
            "suggestions": generate_suggestions(username, domain)
        }
    
    # Check if taken on THIS domain
    if WhydudEmail.objects.filter(username=username.lower(), domain=domain).exists():
        # Check if available on OTHER domains
        other_domains = [d for d in ['whyd.in', 'whyd.click', 'whyd.shop'] if d != domain]
        alternatives = []
        
        for d in other_domains:
            if not WhydudEmail.objects.filter(username=username.lower(), domain=d).exists():
                alternatives.append({"username": username, "domain": d})
        
        suggestions = alternatives + generate_suggestions(username, domain)
        
        return {
            "available": False,
            "reason": "taken",
            "suggestions": suggestions[:6]
        }
    
    return {"available": True, "reason": None, "suggestions": []}


def generate_suggestions(desired: str, preferred_domain: str) -> list[dict]:
    """
    Generate available username+domain combinations.
    Tries same domain first, then other domains.
    """
    all_domains = ['whyd.in', 'whyd.click', 'whyd.shop']
    candidates = []
    
    # Username variations
    variations = [
        f"{desired}26",
        f"{desired}.shop",
        f"the.{desired}",
        f"{desired[0]}{desired}",
        f"{desired}.x",
    ]
    
    for var in variations:
        var = var.lower()[:30]
        # Try preferred domain first
        for domain in [preferred_domain] + [d for d in all_domains if d != preferred_domain]:
            if not WhydudEmail.objects.filter(username=var, domain=domain).exists():
                if not ReservedUsername.objects.filter(username=var).exists():
                    candidates.append({"username": var, "domain": domain})
                    break  # Found one available combo for this variation
    
    return candidates[:5]
```

---

## USER REGISTRATION FLOW (Step 2)

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  📧 Choose your free shopping email                          │
│                                                              │
│  Register this on Amazon, Flipkart, Myntra — we'll          │
│  automatically track all your orders, refunds & returns.     │
│                                                              │
│  ┌────────────────────────┐  ┌──────────────────────┐       │
│  │ ramesh.kumar           │  │  @ whyd.in        ▼  │       │
│  └────────────────────────┘  └──────────────────────┘       │
│                                                              │
│  Domain options:                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                                                       │   │
│  │  ● whyd.in                                            │   │
│  │    ramesh.kumar@whyd.in                               │   │
│  │    Short, professional, India-first                    │   │
│  │                                                       │   │
│  │  ○ whyd.click                                         │   │
│  │    ramesh.kumar@whyd.click                            │   │
│  │    Modern, action-oriented                             │   │
│  │                                                       │   │
│  │  ○ whyd.shop                                          │   │
│  │    ramesh.kumar@whyd.shop                             │   │
│  │    Shopping-focused, descriptive                       │   │
│  │                                                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ✅ ramesh.kumar@whyd.in is available!                       │
│                                                              │
│  [Create My Shopping Email]           [Skip for now →]       │
│                                                              │
│  ⓘ You can change your domain later from Settings.           │
│    Your username stays the same.                             │
└─────────────────────────────────────────────────────────────┘
```

### Frontend: Real-Time Check with Domain Selection

```typescript
"use client";

const DOMAINS = [
  { value: "whyd.in", label: "whyd.in", desc: "Short, professional, India-first" },
  { value: "whyd.click", label: "whyd.click", desc: "Modern, action-oriented" },
  { value: "whyd.shop", label: "whyd.shop", desc: "Shopping-focused, descriptive" },
];

function EmailStep() {
  const [username, setUsername] = useState("");
  const [domain, setDomain] = useState("whyd.in");
  const [status, setStatus] = useState<"idle"|"checking"|"available"|"taken">("idle");
  const [suggestions, setSuggestions] = useState([]);

  // Debounced availability check
  useEffect(() => {
    if (username.length < 3) { setStatus("idle"); return; }
    
    const timer = setTimeout(async () => {
      setStatus("checking");
      const res = await api.email.checkAvailability(username, domain);
      if (res.available) {
        setStatus("available");
        setSuggestions([]);
      } else {
        setStatus("taken");
        setSuggestions(res.suggestions);  // [{username, domain}, ...]
      }
    }, 400);
    
    return () => clearTimeout(timer);
  }, [username, domain]);

  // Re-check when domain changes
  // (username might be available on whyd.shop but not whyd.in)

  return (
    <div>
      <div className="flex gap-2">
        <Input 
          value={username}
          onChange={(e) => setUsername(e.target.value.toLowerCase())}
          placeholder="your.name"
        />
        <span className="text-lg font-medium">@</span>
        <Select value={domain} onValueChange={setDomain}>
          {DOMAINS.map(d => (
            <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
          ))}
        </Select>
      </div>
      
      {status === "checking" && <Spinner />}
      {status === "available" && (
        <p className="text-green-600">✅ {username}@{domain} is available!</p>
      )}
      {status === "taken" && (
        <div>
          <p className="text-red-500">❌ {username}@{domain} is taken</p>
          <p className="text-sm text-slate-600 mt-2">Try one of these:</p>
          <div className="flex flex-wrap gap-2 mt-1">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => { setUsername(s.username); setDomain(s.domain); }}
                className="px-3 py-1 bg-slate-100 rounded-full text-sm hover:bg-primary/10"
              >
                {s.username}@{s.domain}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## API ENDPOINTS

### Check Availability
```
GET /api/v1/email/whydud/check?username=ramesh.kumar&domain=whyd.in

Response (available):
{
  "success": true,
  "data": {
    "username": "ramesh.kumar",
    "domain": "whyd.in",
    "email": "ramesh.kumar@whyd.in",
    "available": true
  }
}

Response (taken):
{
  "success": true,
  "data": {
    "username": "ramesh.kumar",
    "domain": "whyd.in",
    "email": "ramesh.kumar@whyd.in",
    "available": false,
    "reason": "taken",
    "suggestions": [
      {"username": "ramesh.kumar", "domain": "whyd.click"},
      {"username": "ramesh.kumar", "domain": "whyd.shop"},
      {"username": "ramesh.kumar26", "domain": "whyd.in"},
      {"username": "rameshk", "domain": "whyd.in"},
      {"username": "kumar.ramesh", "domain": "whyd.in"}
    ]
  }
}
```

### Create Email
```
POST /api/v1/email/whydud/create
Body: { "username": "ramesh.kumar", "domain": "whyd.in" }

Response:
{
  "success": true,
  "data": {
    "email": "ramesh.kumar@whyd.in",
    "next_steps": [
      "Register this email on Amazon.in",
      "Register this email on Flipkart",
      "Register this email on Myntra"
    ]
  }
}
```

### Change Domain (Settings)
```
PUT /api/v1/email/whydud/domain
Body: { "new_domain": "whyd.shop" }

This changes ramesh.kumar@whyd.in → ramesh.kumar@whyd.shop
Only works if the new combo is available.
Old domain address continues to receive emails for 90 days (grace period).
User must update marketplace registrations.
```

---

## SMART FEATURES ENABLED BY MULTI-DOMAIN

### 1. Domain-Based Analytics
```
"65% of users chose whyd.in, 22% chose whyd.shop, 13% chose whyd.click"
→ Informs marketing and domain investment decisions
```

### 2. A/B Testing Onboarding
```
Show different default domains to different cohorts:
Cohort A: Default whyd.in → measure completion rate
Cohort B: Default whyd.shop → measure completion rate
Winner becomes the new default.
```

### 3. Domain as Social Signal
```
In reviews: "Verified buyer via whyd.in" 
The email domain becomes a trust badge.
Users might prefer one domain for the "cool factor."
```

### 4. Future Domain Expansion
```
If you expand to other countries:
  whyd.uk (UK)
  whyd.us (US)
  whyd.sg (Singapore)

Same architecture, just add MX records and a catch-all rule.
```

### 5. Referral Vanity Domains
```
Premium feature: Custom subdomains for influencers/creators
  tech.whyd.shop   → TechGuru's referral domain
  deals.whyd.click → DealHunter's referral domain

Users who sign up via these get their email on the vanity domain.
Attribution built in.
```

---

## WHAT YOU DON'T NEED (AND WHY)

| Feature | Why You Don't Need It |
|---|---|
| Own SMTP server | You NEVER send from @whyd.* domains. Receive-only. |
| IMAP/POP3 server | Users view emails in Whydud's web inbox, not Outlook/Thunderbird. |
| Spam filter | Cloudflare handles this at the edge before it hits your worker. |
| Email storage server | Emails stored encrypted in PostgreSQL. No need for Dovecot/maildir. |
| Mailgun/SendGrid for @whyd.* | You don't send from these. Only noreply@whydud.com sends (via Resend). |
| MTA (Postfix/Exim) | Cloudflare IS your MTA. It receives and routes. |

---

## COST SUMMARY

| Item | Cost | Notes |
|---|---|---|
| whyd.in domain | ~₹700/yr | Already purchased |
| whyd.click domain | ~₹200/yr | Already purchased |
| whyd.shop domain | ~₹2000/yr | Already purchased |
| Cloudflare Email Routing (all 3) | Free | Unlimited routing |
| Cloudflare Email Workers | Free | 100K invocations/day |
| Resend (sending from whydud.com) | Free → $20/mo | 100/day free |
| **Total** | **~₹3000/yr + $0-20/mo** | Effectively free at launch |

An own email server would cost $50-200/month + weeks of setup + ongoing maintenance. You save all of that.
