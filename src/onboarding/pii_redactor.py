"""
Sprint 27 — PII redactor for client review data.

Applies regex-based redaction to signal strings in order:
  1. Email addresses        → [EMAIL]
  2. Indian mobile numbers  → [PHONE]
  3. Aadhaar-pattern IDs    → [ID]
  4. Honorific-prefixed names (Dr/Mr/Mrs/Ms) → [NAME]

No LLM calls. Deterministic. Uses re module only.
"""

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Compiled patterns — defined once at module level for performance
# ---------------------------------------------------------------------------

# 1. Email: handles user@domain.com, user.name+tag@subdomain.co.uk
EMAIL_PATTERN = re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+')

# 2. Indian mobile: 10-digit number starting 6–9, optionally prefixed +91
#    with optional space or dash separator.
#    Lookbehind excludes digits AND letters so +91XXXXXXXXXX is matched in full
#    (the '+' is neither a digit nor a letter, so (?<![0-9A-Za-z]) allows it).
#    Lookahead prevents matching a digit tail inside a longer number.
PHONE_PATTERN = re.compile(r'(?<![0-9A-Za-z])(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)')

# 3. Aadhaar: 12 digits, optionally split into three groups of 4 by space/dash.
#    Word-boundary anchors stop it from matching inside longer numbers.
ID_PATTERN = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')

# 4. Honorific + capitalised word that follows.
#    Matches Dr, Mr, Mrs, Ms — with or without trailing period — then a
#    mandatory space and a word that starts with a capital letter.
#    Generic capitalised words (Mumbai, Apple…) are NOT touched because there
#    is no honorific in front of them.
NAME_PATTERN = re.compile(r'\b(Dr|Mr|Mrs|Ms)\.?\s+[A-Z][a-z]+')


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RedactionLog:
    n_emails_redacted: int = 0
    n_phones_redacted: int = 0
    n_ids_redacted: int = 0      # Aadhaar-pattern
    n_names_redacted: int = 0    # Dr./Mr./Mrs./Ms. + following word
    total_signals_affected: int = 0

    def summary(self) -> str:
        return (
            f"emails={self.n_emails_redacted}, phones={self.n_phones_redacted}, "
            f"ids={self.n_ids_redacted}, names={self.n_names_redacted}, "
            f"signals_affected={self.total_signals_affected}"
        )


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def redact_pii(signals: list[str]) -> tuple[list[str], RedactionLog]:
    """
    Apply PII redaction to each signal string.

    Patterns (applied in order):
    1. Email: r'[\\w.+-]+@[\\w-]+\\.[\\w.]+'           → [EMAIL]
    2. Indian mobile: r'(?:\\+91[\\s-]?)?[6-9]\\d{9}'  → [PHONE]
    3. Aadhaar-pattern: r'\\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b' → [ID]
    4. Honorific names: r'\\b(Dr|Mr|Mrs|Ms)\\.?\\s+[A-Z][a-z]+'   → [NAME]

    Rules:
    - No generic first-name detection — ONLY redact when preceded by Dr./Mr./Mrs./Ms.
    - A signal is "affected" if any redaction was applied to it.
    - Counts track total replacements across all signals (not unique).
    - Returns (redacted_signals, RedactionLog).
    - Never raises — returns original signal unchanged on any error.
    """
    log = RedactionLog()
    redacted: list[str] = []

    for signal in signals:
        try:
            original = signal

            # 1. Emails
            text, n = re.subn(EMAIL_PATTERN, '[EMAIL]', signal)
            log.n_emails_redacted += n

            # 2. Indian mobile numbers
            text, n = re.subn(PHONE_PATTERN, '[PHONE]', text)
            log.n_phones_redacted += n

            # 3. Aadhaar-pattern IDs
            text, n = re.subn(ID_PATTERN, '[ID]', text)
            log.n_ids_redacted += n

            # 4. Honorific-prefixed names
            text, n = re.subn(NAME_PATTERN, '[NAME]', text)
            log.n_names_redacted += n

            if text != original:
                log.total_signals_affected += 1

            redacted.append(text)

        except Exception:
            # Never raise — return the original signal untouched on any error
            redacted.append(signal)

    return redacted, log
