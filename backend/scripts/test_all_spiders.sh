#!/usr/bin/env bash
#
# test_all_spiders.sh — Connectivity test for untested production spiders
#
# Runs each spider with --max-pages 1 against a single test URL inside the
# celery-worker Docker container. Logs exit code, item count, and elapsed time.
#
# Usage:
#   cd /path/to/whydud/docker
#   bash ../backend/scripts/test_all_spiders.sh
#
# Prerequisites:
#   - Docker Compose stack is running (docker compose ps)
#   - Run from the docker/ directory (where docker-compose.yml lives)

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

COMPOSE_SERVICE="celery-worker"
LOG_DIR="/tmp/spider_tests_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

# Spiders to test: spider_name|test_url|notes
declare -a SPIDERS=(
  "croma|https://www.croma.com/phones-wearables/mobile-phones/c/10|curl_cffi Chrome TLS"
  "meesho|https://www.meesho.com/mobile-phones/pl/mobiles|camoufox anti-detect Firefox"
  "ajio|https://www.ajio.com/shop/men-shoes|Playwright + PerimeterX"
  "myntra|https://www.myntra.com/men-tshirts|Playwright + fingerprinting"
  "firstcry|https://www.firstcry.com/toys|curl_cffi Chrome/131"
  "nykaa|https://www.nykaa.com/skin/c/2?root=nav_2|curl_cffi Chrome/120 (partially tested)"
  "jiomart|https://www.jiomart.com/c/groceries/fruits-vegetables/fresh-vegetables/229|curl_cffi + sitemap (partially tested)"
)

# ── Colours ──────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Pre-flight checks ───────────────────────────────────────────────────────

echo -e "${BOLD}=== Whydud Spider Production Test ===${NC}"
echo -e "Started: $(date)"
echo -e "Log dir: ${CYAN}${LOG_DIR}${NC}"
echo ""

# Verify Docker Compose is running
if ! docker compose ps --format '{{.Service}}' 2>/dev/null | grep -q "$COMPOSE_SERVICE"; then
  echo -e "${RED}ERROR: ${COMPOSE_SERVICE} is not running.${NC}"
  echo "Start the stack first: docker compose up -d"
  exit 1
fi

echo -e "${GREEN}✓ ${COMPOSE_SERVICE} container is running${NC}"
echo ""

# ── Result storage ───────────────────────────────────────────────────────────

declare -a RESULTS=()  # "spider|exit_code|items|elapsed|status"

# ── Run each spider ─────────────────────────────────────────────────────────

TOTAL=${#SPIDERS[@]}
CURRENT=0

for entry in "${SPIDERS[@]}"; do
  IFS='|' read -r spider_name test_url notes <<< "$entry"
  CURRENT=$((CURRENT + 1))

  echo -e "${BOLD}[${CURRENT}/${TOTAL}] Testing: ${CYAN}${spider_name}${NC} (${notes})"
  echo -e "  URL: ${test_url}"

  log_file="${LOG_DIR}/${spider_name}.log"
  start_time=$(date +%s)

  # Run spider inside Docker container
  # --max-pages 1 ensures we only scrape 1 listing page
  # --urls overrides seed URLs with our test URL
  set +e
  docker compose exec -T "$COMPOSE_SERVICE" \
    python -m apps.scraping.runner "$spider_name" \
      --max-pages 1 \
      --urls "$test_url" \
    > "$log_file" 2>&1
  exit_code=$?
  set -e

  end_time=$(date +%s)
  elapsed=$((end_time - start_time))

  # Try to get item count from the log output (Scrapy stats line)
  items_scraped=$(grep -oP "'item_scraped_count':\s*\K\d+" "$log_file" 2>/dev/null || echo "0")

  # Determine status
  if [ "$exit_code" -eq 0 ] && [ "$items_scraped" -gt 0 ]; then
    status="PASS"
    status_color="${GREEN}"
  elif [ "$exit_code" -eq 0 ] && [ "$items_scraped" -eq 0 ]; then
    status="WARN"
    status_color="${YELLOW}"
  else
    status="FAIL"
    status_color="${RED}"
  fi

  echo -e "  Result: ${status_color}${status}${NC} | Exit: ${exit_code} | Items: ${items_scraped} | Time: ${elapsed}s"

  # On failure or warning, show last 20 lines of log
  if [ "$status" != "PASS" ]; then
    echo -e "  ${YELLOW}--- Last 20 lines of output ---${NC}"
    tail -20 "$log_file" | sed 's/^/  | /'
    echo -e "  ${YELLOW}--- End of output ---${NC}"
  fi

  echo ""

  RESULTS+=("${spider_name}|${exit_code}|${items_scraped}|${elapsed}|${status}")
done

# ── Summary Table ────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║                    SPIDER TEST SUMMARY                      ║${NC}"
echo -e "${BOLD}╠══════════════════╦══════╦═══════╦════════╦══════════════════╣${NC}"
printf  "${BOLD}║ %-16s ║ Exit ║ Items ║  Time  ║ Status           ║${NC}\n" "Spider"
echo -e "${BOLD}╠══════════════════╬══════╬═══════╬════════╬══════════════════╣${NC}"

pass_count=0
fail_count=0
warn_count=0

for result in "${RESULTS[@]}"; do
  IFS='|' read -r spider_name exit_code items elapsed status <<< "$result"

  case "$status" in
    PASS) status_display="${GREEN}PASS${NC}"; pass_count=$((pass_count + 1)) ;;
    WARN) status_display="${YELLOW}WARN (0 items)${NC}"; warn_count=$((warn_count + 1)) ;;
    FAIL) status_display="${RED}FAIL${NC}"; fail_count=$((fail_count + 1)) ;;
  esac

  printf "║ %-16s ║  %2s  ║  %3s  ║ %4ss  ║ " "$spider_name" "$exit_code" "$items" "$elapsed"
  echo -e "${status_display}$(printf '%*s' $((16 - ${#status})) '')║"
done

echo -e "${BOLD}╚══════════════════╩══════╩═══════╩════════╩══════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}PASS: ${pass_count}${NC}  ${YELLOW}WARN: ${warn_count}${NC}  ${RED}FAIL: ${fail_count}${NC}  Total: ${TOTAL}"
echo ""
echo -e "Full logs: ${CYAN}${LOG_DIR}/${NC}"
echo -e "Finished: $(date)"

# ── Exit with non-zero if any spider failed ──────────────────────────────────

if [ "$fail_count" -gt 0 ]; then
  echo ""
  echo -e "${YELLOW}NOTE: Some failures may be expected due to geo-blocking or"
  echo -e "anti-bot protection requiring Indian proxy/IP. Check individual"
  echo -e "logs for details.${NC}"
  exit 1
fi
