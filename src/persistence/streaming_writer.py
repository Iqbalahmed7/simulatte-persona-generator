"""StreamingCohortWriter — progressive, checkpoint-safe persona-to-disk writer.

Solves two distinct problems that arise at larger cohort sizes:

1.  **Context-limit resilience** (programmatic pipeline)
    When generating 30+ personas via the orchestrator, ``asyncio.gather()``
    holds everything in memory until the very end.  If the process is
    interrupted (crash, timeout, API error) after persona #22, all work is
    lost.  StreamingCohortWriter checkpoints each persona to disk the moment
    it is produced, so a re-run can skip already-written personas.

2.  **LLM-agent output limits** (Claude skill context)
    When the Persona Generator skill (Claude Code) generates personas as text
    output, a single response producing 30 full persona dicts exceeds token
    limits.  The skill can instead generate one persona at a time, call
    ``writer.append()`` after each, and the writer handles all disk I/O.
    The skill only ever holds one persona in its active context.

Auto-trigger rule
-----------------
Both ``invoke_persona_generator()`` and ``_run_generation()`` check
``StreamingCohortWriter.should_stream(count)`` before deciding whether to
use streaming.  The threshold is ``STREAMING_THRESHOLD`` (default: 8,
configurable via the ``PG_STREAMING_THRESHOLD`` env var).

Temp directory layout
---------------------
During a run, personas are written to a hidden staging directory alongside
the target output file::

    {output_dir}/
      .stream_{cohort_id}/
        meta.json           # cohort-level metadata (no personas array)
        p_0001.json         # one file per persona, zero-padded index
        p_0002.json
        ...
        checkpoint.json     # written persona IDs + progress tracking
      {cohort_id}.json      # final merged output (written by finalize())

``finalize()`` reads all ``p_*.json`` files in order, assembles the complete
cohort JSON, writes ``{cohort_id}.json``, then deletes the staging directory.
If a ``{cohort_id}.json`` file already exists (from a prior complete run)
``finalize()`` does not overwrite it — call ``overwrite=True`` to force.

Resume
------
If a staging directory already exists when ``begin()`` is called, the writer
enters resume mode: ``written_ids`` is loaded from ``checkpoint.json`` and
``append()`` silently skips any persona whose ID is already in that set.
The caller (skill or pipeline) can query ``writer.already_written`` to skip
generating personas that are already on disk.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StreamingCohortWriter:
    """Write cohort personas to disk one at a time, with checkpoint/resume."""

    # Auto-streaming threshold: use streaming when count >= this value.
    # Override via PG_STREAMING_THRESHOLD env var (integer).
    STREAMING_THRESHOLD: int = int(os.environ.get("PG_STREAMING_THRESHOLD", "8"))

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def __init__(self, output_dir: str | Path, cohort_id: str) -> None:
        """
        Args:
            output_dir: Directory where the final ``{cohort_id}.json`` will live.
            cohort_id:  Unique identifier for this cohort run.
        """
        self._output_dir = Path(output_dir)
        self._cohort_id = cohort_id
        self._staging_dir = self._output_dir / f".stream_{cohort_id}"
        self._final_path = self._output_dir / f"{cohort_id}.json"
        self._checkpoint_path = self._staging_dir / "checkpoint.json"
        self._meta_path = self._staging_dir / "meta.json"

        # Runtime state
        self._index: int = 0           # next sequential write index
        self._written_ids: set[str] = set()
        self._started: bool = False

    @classmethod
    def should_stream(cls, count: int) -> bool:
        """Return True if *count* personas is large enough to warrant streaming."""
        return count >= cls.STREAMING_THRESHOLD

    @classmethod
    def for_run(
        cls,
        output_dir: str | Path,
        cohort_id: str,
    ) -> "StreamingCohortWriter":
        """Factory — preferred constructor for orchestrator / skill callers."""
        return cls(output_dir=output_dir, cohort_id=cohort_id)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def already_written(self) -> set[str]:
        """Set of persona IDs that have already been persisted.

        Populated after ``begin()`` (including resume cases).  The skill or
        pipeline can use this to skip generating personas that don't need
        re-generating.
        """
        return frozenset(self._written_ids)  # type: ignore[return-value]

    @property
    def output_path(self) -> Path:
        """Path where the final merged cohort JSON will be written."""
        return self._final_path

    @property
    def staging_dir(self) -> Path:
        """Path to the temporary staging directory."""
        return self._staging_dir

    def can_resume(self) -> bool:
        """Return True if a prior incomplete run exists and can be resumed."""
        return self._checkpoint_path.exists()

    def begin(self, cohort_metadata: dict[str, Any]) -> None:
        """Initialise (or resume) a streaming run.

        Writes cohort-level metadata (everything except the personas array) to
        ``meta.json`` in the staging directory.  If a prior staging directory
        already exists, loads the checkpoint and enters resume mode — metadata
        is NOT overwritten in that case.

        Args:
            cohort_metadata: Dict of cohort-level fields (cohort_id,
                generated_at, domain, business_problem, etc.) — without the
                ``personas`` key.
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)

        if self.can_resume():
            # Resume mode: load existing checkpoint
            ckpt = json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
            self._written_ids = set(ckpt.get("written_ids", []))
            self._index = ckpt.get("next_index", len(self._written_ids))
            _log(
                f"[streaming_writer] Resume mode — "
                f"{len(self._written_ids)} persona(s) already on disk, "
                f"continuing from index {self._index + 1}."
            )
        else:
            # Fresh start
            self._staging_dir.mkdir(parents=True, exist_ok=True)
            # Strip personas key if accidentally included
            meta = {k: v for k, v in cohort_metadata.items() if k != "personas"}
            self._meta_path.write_text(
                json.dumps(meta, indent=2, default=str), encoding="utf-8"
            )
            self._written_ids = set()
            self._index = 0
            self._save_checkpoint()
            _log(
                f"[streaming_writer] Started fresh run — "
                f"cohort_id={self._cohort_id}, staging={self._staging_dir}"
            )

        self._started = True

    def append(self, persona_dict: dict[str, Any]) -> None:
        """Append one persona to the staging directory and update checkpoint.

        Silently skips personas whose ``persona_id`` is already in
        ``already_written`` (safe to call idempotently on resume).

        Args:
            persona_dict: A fully-populated persona dict conforming to the
                output schema.  Must contain a ``persona_id`` field.

        Raises:
            RuntimeError: If ``begin()`` has not been called.
        """
        if not self._started:
            raise RuntimeError(
                "StreamingCohortWriter.begin() must be called before append()."
            )

        pid = persona_dict.get("persona_id", f"unknown-{self._index:04d}")

        if pid in self._written_ids:
            _log(f"[streaming_writer] Skipping {pid} (already written).")
            return

        self._index += 1
        filename = f"p_{self._index:04d}.json"
        persona_path = self._staging_dir / filename
        persona_path.write_text(
            json.dumps(persona_dict, indent=2, default=str), encoding="utf-8"
        )

        self._written_ids.add(pid)
        self._save_checkpoint()
        _log(
            f"[streaming_writer] Wrote persona {self._index} — "
            f"{pid} → {filename}"
        )

    def finalize(
        self,
        cohort_summary: dict[str, Any] | None = None,
        *,
        envelope_meta: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> Path:
        """Merge staging files into the final cohort JSON and clean up.

        Reads ``meta.json`` + all ``p_*.json`` files (in order) from the
        staging directory, assembles the complete cohort envelope dict, writes
        it to ``{output_dir}/{cohort_id}.json``, then removes the staging
        directory.

        Args:
            cohort_summary: Optional cohort-level summary dict to embed.  If
                ``None``, any ``cohort_summary`` already present in
                ``meta.json`` is preserved.
            envelope_meta: If provided, replaces the ``meta.json`` content as
                the base of the final envelope.  Use this to pass the full
                ``CohortEnvelope`` dict (minus ``personas``) so that all
                required Pydantic fields are present in the output file.
                When ``None``, the partial metadata written by ``begin()`` is
                used as the base (suitable when the caller only needs a raw
                JSON file, not Pydantic-validated output).
            overwrite: If True, overwrite an existing final output file.

        Returns:
            Path to the written final JSON file.

        Raises:
            RuntimeError: If the final output already exists and
                ``overwrite=False``.
            FileNotFoundError: If the staging directory does not exist.
        """
        if not self._staging_dir.exists():
            raise FileNotFoundError(
                f"Staging directory not found: {self._staging_dir}. "
                "Did you call begin() first?"
            )

        if self._final_path.exists() and not overwrite:
            raise RuntimeError(
                f"Output file already exists: {self._final_path}. "
                "Pass overwrite=True to replace it."
            )

        # --- Load metadata ---
        if envelope_meta is not None:
            # Caller supplied the full envelope structure — use it directly,
            # stripping the personas key so we can inject our own ordered list.
            cohort_data: dict[str, Any] = {
                k: v for k, v in envelope_meta.items() if k != "personas"
            }
        else:
            if not self._meta_path.exists():
                raise FileNotFoundError(
                    f"Metadata file not found: {self._meta_path}"
                )
            cohort_data = json.loads(
                self._meta_path.read_text(encoding="utf-8")
            )

        # --- Load personas ---
        # If the caller supplied an envelope_meta that already contains a
        # ``personas`` list (e.g. the stratified 30 selected by assemble_cohort),
        # use that list directly rather than re-reading all staging files.
        # This is the correct behaviour when stratification reduces the candidate
        # pool (e.g. 60 candidates → 30 selected): the staging dir holds all 60,
        # but the authoritative selection is in the envelope.
        if envelope_meta is not None and "personas" in envelope_meta:
            personas: list[dict] = envelope_meta["personas"]
            # Remove from cohort_data so we don't double-set it below
            cohort_data.pop("personas", None)
        else:
            persona_files = sorted(
                self._staging_dir.glob("p_*.json"),
                key=lambda p: p.name,
            )
            personas = []
            for pf in persona_files:
                personas.append(json.loads(pf.read_text(encoding="utf-8")))

        _log(
            f"[streaming_writer] Merging {len(personas)} persona(s) "
            f"into {self._final_path.name}…"
        )

        # --- Assemble final envelope ---
        cohort_data["personas"] = personas

        if cohort_summary is not None:
            cohort_data["cohort_summary"] = cohort_summary
        # (else: preserve cohort_summary already in meta.json / envelope_meta if present)

        # Only add streaming housekeeping metadata when we're NOT writing a
        # Pydantic-validated CohortEnvelope (envelope_meta=None means the caller
        # owns the schema; envelope_meta supplied means strict schema compliance needed).
        if envelope_meta is None:
            cohort_data["_streaming_meta"] = {
                "streamed": True,
                "persona_count": len(personas),
                "finalized_at": datetime.now(timezone.utc).isoformat(),
            }

        # --- Write final output ---
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._final_path.write_text(
            json.dumps(cohort_data, indent=2, default=str), encoding="utf-8"
        )

        # --- Clean up staging directory ---
        shutil.rmtree(self._staging_dir)
        _log(
            f"[streaming_writer] Finalised → {self._final_path} "
            f"(staging directory removed)."
        )

        return self._final_path

    def abort(self) -> None:
        """Remove the staging directory without producing a final output.

        Use when a run is intentionally cancelled.  Does not remove any
        previously finalised output file.
        """
        if self._staging_dir.exists():
            shutil.rmtree(self._staging_dir)
            _log(f"[streaming_writer] Aborted — staging directory removed.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _save_checkpoint(self) -> None:
        """Persist current progress to checkpoint.json."""
        ckpt = {
            "cohort_id": self._cohort_id,
            "written_ids": sorted(self._written_ids),
            "next_index": self._index,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._checkpoint_path.write_text(
            json.dumps(ckpt, indent=2), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# Internal logging helper
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:
    """Emit a progress message to stderr (same channel as click.echo(..., err=True))."""
    import sys
    print(msg, file=sys.stderr)
