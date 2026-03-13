"""ANSI color formatter for backfill pipeline logs.

Applies regex-based colorization to log messages so different phases,
outcomes, and components are visually distinct in terminal output.

Hooked into Celery worker logging via ``setup_logging`` signal in
``whydud/celery.py``.
"""
from __future__ import annotations

import logging
import re


# ── ANSI escape codes ────────────────────────────────────────────
class C:
    """ANSI color/style constants."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Standard
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"

    # Bright
    B_RED = "\033[91m"
    B_GREEN = "\033[92m"
    B_YELLOW = "\033[93m"
    B_BLUE = "\033[94m"
    B_MAGENTA = "\033[95m"
    B_CYAN = "\033[96m"
    B_WHITE = "\033[97m"

    # Backgrounds (subtle)
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"


# ── Pattern rules ────────────────────────────────────────────────
# Each rule: (compiled_regex, replacement_template)
# Applied in order; first match per position wins.

_RULES: list[tuple[re.Pattern, str]] = [
    # Phase labels — each phase gets a unique color
    (re.compile(r"(Phase\s*0)"), f"{C.DIM}{C.CYAN}\\1{C.RESET}"),
    (re.compile(r"(Phase\s*1)"), f"{C.BOLD}{C.CYAN}\\1{C.RESET}"),
    (re.compile(r"(Phase\s*2)"), f"{C.BOLD}{C.BLUE}\\1{C.RESET}"),
    (re.compile(r"(Phase\s*3)"), f"{C.BOLD}{C.B_MAGENTA}\\1{C.RESET}"),
    (re.compile(r"(Phase\s*4)"), f"{C.BOLD}{C.YELLOW}\\1{C.RESET}"),

    # Worker tags [W-xxxxxx] — bright yellow, very visible
    (re.compile(r"(\[W-[a-f0-9]+\])"), f"{C.BOLD}{C.B_YELLOW}\\1{C.RESET}"),

    # HTTP status codes
    (re.compile(r'\b(200 OK|"HTTP/1\.1 200 OK")'), f"{C.GREEN}\\1{C.RESET}"),
    (re.compile(r"\b(403 Forbidden|403|429)\b"), f"{C.B_RED}\\1{C.RESET}"),
    (re.compile(r'"HTTP/1\.1 (403 Forbidden)"'), f'"HTTP/1.1 {C.B_RED}\\1{C.RESET}"'),

    # Proxy mode indicators
    (re.compile(r"(via proxy)"), f"{C.CYAN}\\1{C.RESET}"),
    (re.compile(r"(via direct)"), f"{C.BLUE}\\1{C.RESET}"),
    (re.compile(r"\((probe)\)"), f"({C.B_YELLOW}\\1{C.RESET})"),
    (re.compile(r"(Proxy strategy:)"), f"{C.BOLD}{C.CYAN}\\1{C.RESET}"),

    # Proxy state changes
    (re.compile(r"(switching to PROXY)"), f"{C.BOLD}{C.CYAN}\\1{C.RESET}"),
    (re.compile(r"(switching back to DIRECT)"), f"{C.BOLD}{C.GREEN}\\1{C.RESET}"),
    (re.compile(r"(direct IP recovered)"), f"{C.BOLD}{C.B_GREEN}\\1{C.RESET}"),
    (re.compile(r"(direct IP burned)"), f"{C.BOLD}{C.B_RED}\\1{C.RESET}"),
    (re.compile(r"(rotating IP)"), f"{C.CYAN}\\1{C.RESET}"),
    (re.compile(r"(probing direct IP)"), f"{C.B_YELLOW}\\1{C.RESET}"),

    # Success outcomes
    (re.compile(r"\b(OK)\b"), f"{C.GREEN}\\1{C.RESET}"),
    (re.compile(r"\b(complete|completed|done)\b", re.I), f"{C.GREEN}\\1{C.RESET}"),
    (re.compile(r"\b(\d+)\s+(extended)\b"), f"{C.BOLD}{C.GREEN}\\1{C.RESET} {C.GREEN}\\2{C.RESET}"),
    (re.compile(r"\b(\d+)\s+(filled)\b"), f"{C.BOLD}{C.GREEN}\\1{C.RESET} {C.GREEN}\\2{C.RESET}"),
    (re.compile(r"\b(\d+)\s+(injected)\b"), f"{C.BOLD}{C.GREEN}\\1{C.RESET} {C.GREEN}\\2{C.RESET}"),
    (re.compile(r"\b(\d+)\s+(created)\b"), f"{C.BOLD}{C.GREEN}\\1{C.RESET} {C.GREEN}\\2{C.RESET}"),

    # Failure outcomes
    (re.compile(r"\b(failed|failure|error)\b", re.I), f"{C.B_RED}\\1{C.RESET}"),
    (re.compile(r"\b(burned)\b"), f"{C.B_RED}\\1{C.RESET}"),
    (re.compile(r"\b(token_failed)\b"), f"{C.RED}\\1{C.RESET}"),
    (re.compile(r"\b(api_failed)\b"), f"{C.RED}\\1{C.RESET}"),

    # Warning outcomes
    (re.compile(r"\b(rate_limited|rate.limited)\b"), f"{C.B_YELLOW}\\1{C.RESET}"),
    (re.compile(r"\b(cooldown)\b", re.I), f"{C.YELLOW}\\1{C.RESET}"),
    (re.compile(r"\b(skip(?:ping|ped)?)\b", re.I), f"{C.YELLOW}\\1{C.RESET}"),
    (re.compile(r"\b(stopping)\b", re.I), f"{C.BOLD}{C.B_YELLOW}\\1{C.RESET}"),

    # Wave progress — dim for less visual noise
    (re.compile(r"(wave \d+/\d+)"), f"{C.DIM}\\1{C.RESET}"),

    # PH / BH client labels
    (re.compile(r"\b(PH HTML)\b"), f"{C.MAGENTA}\\1{C.RESET}"),
    (re.compile(r"\b(PH API)\b"), f"{C.B_MAGENTA}\\1{C.RESET}"),
    (re.compile(r"\b(PH HTTP)\b"), f"{C.MAGENTA}\\1{C.RESET}"),
    (re.compile(r"\b(BH API|BH HTTP)\b"), f"{C.B_BLUE}\\1{C.RESET}"),
    (re.compile(r"\b(BH burst pause|BH cooldown)\b"), f"{C.YELLOW}\\1{C.RESET}"),

    # Request counter (req #NNN)
    (re.compile(r"(\(req #\d+\))"), f"{C.DIM}\\1{C.RESET}"),

    # Claimed/released counts
    (re.compile(r"\b(claimed)\b"), f"{C.B_CYAN}\\1{C.RESET}"),
    (re.compile(r"\b(released)\b"), f"{C.YELLOW}\\1{C.RESET}"),

    # Repeat round info
    (re.compile(r"(round \d+)"), f"{C.BOLD}\\1{C.RESET}"),

    # Points with comma formatting
    (re.compile(r"\b(\d{1,3}(?:,\d{3})+)\s+(points)"), f"{C.BOLD}{C.B_GREEN}\\1{C.RESET} \\2"),
]


def colorize(message: str) -> str:
    """Apply ANSI color codes to a log message based on pattern rules."""
    for pattern, replacement in _RULES:
        message = pattern.sub(replacement, message)
    return message


# ── Custom Formatter ─────────────────────────────────────────────

class BackfillColorFormatter(logging.Formatter):
    """Logging formatter that adds ANSI colors to backfill pipeline messages.

    Also colors the log level itself:
      - DEBUG: dim
      - INFO: default
      - WARNING: yellow
      - ERROR/CRITICAL: red
    """

    LEVEL_COLORS = {
        logging.DEBUG: C.DIM,
        logging.INFO: "",
        logging.WARNING: C.B_YELLOW,
        logging.ERROR: C.B_RED,
        logging.CRITICAL: f"{C.BOLD}{C.B_RED}",
    }

    def format(self, record: logging.LogRecord) -> str:
        # Format the base message
        formatted = super().format(record)

        # Apply pattern-based colorization to the message portion
        formatted = colorize(formatted)

        # Color the level name
        level_color = self.LEVEL_COLORS.get(record.levelno, "")
        if level_color:
            formatted = formatted.replace(
                record.levelname,
                f"{level_color}{record.levelname}{C.RESET}",
                1,
            )

        return formatted
