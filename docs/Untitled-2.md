read @CLAUDE.md @docs/ARCHITECTURE.md @PROGRESS.md @docs/design-system.md TASK: Configure whyd.click and whyd.shop domains for email per architecture.md §6

This is primarily a DNS/infrastructure task. The code already handles multi-domain (WhydudEmail has domain field, webhook parses from recipient address).

STEPS:

   

4. VERIFY:
send test email from no-reply@whydud.com from resend with api re_NUtYFKyg_Ks6pHECRHSaeR69XfFJnzGwH
   Send test email to test@whyd.click → should appear in Django webhook logs
   Send test email to test@whyd.shop → should appear in Django webhook logs same for whyd.in

5. CODE VERIFICATION:
   Confirm these already work in backend:
   - WhydudEmail model accepts domain='whyd.click' and 'whyd.shop' and 'whyd.in'
   - Email webhook handler parses domain from recipient address
   - Registration step 2 shows domain selector (whyd.in / whyd.click / whyd.shop)
   If any code changes needed, make them.