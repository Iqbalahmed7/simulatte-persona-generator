"""
ingestion.py — Upload orchestrator for the Simulatte onboarding pipeline.
Sprint 27 · No LLM calls in this module itself.

Ties together:
  format_inferrer  → detect format, parse to signals
  pii_redactor     → redact PII from signals          (written by another engineer)
  ingestion_validator → validate the redacted corpus  (written by another engineer)
  signal_tagger    → optionally tag signals via LLM   (written by another engineer)

All three collaborator modules are imported lazily inside `ingest()` to avoid
circular-import issues while the sprint is still in progress.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IngestionResult:
    raw_signals: list[str]         # signals after parsing, before PII redaction
    redacted_signals: list[str]    # signals after PII redaction
    redaction_log: Any             # RedactionLog from pii_redactor
    format_detected: str           # DataFormat.value
    validation_report: Any         # ValidationReport from ingestion_validator
    tagged_corpus: Any | None      # TaggedCorpus from signal_tagger (None if not tagged)
    ready_for_grounding: bool      # True when validation_report.is_valid


def ingest(
    raw_bytes: bytes,
    run_tagger: bool = False,
    llm_client: Any = None,
) -> IngestionResult:
    """
    Full ingestion pipeline:

    1. infer_format(raw_bytes)                          → DataFormat
    2. parse_to_signals(raw_bytes)                      → list[str]
    3. pii_redactor.redact_pii(signals)                 → (redacted_signals, redaction_log)
    4. ingestion_validator.validate_corpus(redacted)    → ValidationReport
    5. If run_tagger=True: signal_tagger.tag_signals(redacted_signals, llm_client)
       else: tagged_corpus = None
    6. Return IngestionResult

    No LLM calls are made by this function itself; the tagger is invoked only
    when run_tagger=True and an llm_client is supplied by the caller.
    """
    # Lazy imports — collaborator modules may not exist yet at load time
    from src.onboarding.format_inferrer import infer_format, parse_to_signals
    from src.onboarding.pii_redactor import redact_pii
    from src.onboarding.ingestion_validator import validate_corpus

    # Step 1 — detect format
    fmt = infer_format(raw_bytes)

    # Step 2 — parse to flat signal strings
    raw_signals: list[str] = parse_to_signals(raw_bytes)

    # Step 3 — redact PII
    redacted_signals, redaction_log = redact_pii(raw_signals)

    # Step 4 — validate corpus
    validation_report = validate_corpus(redacted_signals)

    # Step 5 — optional tagging (requires llm_client)
    if run_tagger:
        from src.onboarding.signal_tagger import tag_signals
        tagged_corpus = tag_signals(redacted_signals, llm_client)
    else:
        tagged_corpus = None

    return IngestionResult(
        raw_signals=raw_signals,
        redacted_signals=redacted_signals,
        redaction_log=redaction_log,
        format_detected=fmt.value,
        validation_report=validation_report,
        tagged_corpus=tagged_corpus,
        ready_for_grounding=validation_report.is_valid,
    )
