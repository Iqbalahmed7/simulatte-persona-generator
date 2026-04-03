"""src/registry/persona_registry.py — Central persona registry.

Persistent file store: data/registry/personas/{persona_id}.json
Index file: data/registry/index/registry_index.json

No LLM calls.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.schema.persona import PersonaRecord


@dataclass
class RegistryEntry:
    persona_id: str
    age: int
    gender: str          # "female" | "male" | "non-binary"
    city_tier: str       # "metro" | "tier2" | "tier3" | "rural"
    domain: str
    registered_at: str   # ISO datetime string
    version: str = "1.0"


class PersonaRegistry:
    """Central persistent registry for PersonaRecord objects.

    File layout:
        {registry_path}/personas/{persona_id}.json  — full PersonaRecord
        {registry_path}/index/registry_index.json   — list[RegistryEntry dicts]

    All methods are synchronous. No LLM calls.
    """

    DEFAULT_PATH = Path("data/registry")

    def __init__(self, registry_path: str | Path | None = None):
        self._root = Path(registry_path) if registry_path else self.DEFAULT_PATH
        self._personas_dir = self._root / "personas"
        self._index_path = self._root / "index" / "registry_index.json"
        self._personas_dir.mkdir(parents=True, exist_ok=True)
        self._index_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Index helpers
    # ------------------------------------------------------------------

    def _load_index(self) -> list[RegistryEntry]:
        """Load the registry index from disk. Returns [] if not found."""
        if not self._index_path.exists():
            return []
        data = json.loads(self._index_path.read_text())
        return [RegistryEntry(**d) for d in data]

    def _save_index(self, entries: list[RegistryEntry]) -> None:
        """Persist the full index to disk as JSON."""
        self._index_path.write_text(json.dumps([asdict(e) for e in entries], indent=2))

    def _entry_from_persona(self, persona: PersonaRecord) -> RegistryEntry:
        """Build a RegistryEntry from a PersonaRecord."""
        return RegistryEntry(
            persona_id=persona.persona_id,
            age=persona.demographic_anchor.age,
            gender=persona.demographic_anchor.gender,
            city_tier=persona.demographic_anchor.location.urban_tier,
            domain=persona.domain,
            registered_at=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, persona: PersonaRecord) -> RegistryEntry:
        """Add or replace a persona in the registry.

        - Writes {persona_id}.json to personas dir (full PersonaRecord, via model_dump_json)
        - Updates registry_index.json (replace if persona_id exists, else append)
        - Returns the RegistryEntry for the added persona
        - Idempotent: calling add() twice with the same persona_id overwrites
        """
        persona_path = self._personas_dir / f"{persona.persona_id}.json"
        persona_path.write_text(persona.model_dump_json(indent=2))

        entry = self._entry_from_persona(persona)

        entries = self._load_index()
        updated = [e for e in entries if e.persona_id != persona.persona_id]
        updated.append(entry)
        self._save_index(updated)

        return entry

    def get(self, persona_id: str) -> PersonaRecord | None:
        """Load a PersonaRecord by ID. Returns None if not found."""
        path = self._personas_dir / f"{persona_id}.json"
        if not path.exists():
            return None
        return PersonaRecord.model_validate_json(path.read_text())

    def find(
        self,
        age_min: int | None = None,
        age_max: int | None = None,
        gender: str | None = None,
        city_tier: str | None = None,
        domain: str | None = None,
    ) -> list[RegistryEntry]:
        """Query registry by demographic criteria (AND logic).

        All parameters are optional. Omitting a parameter means no filter on that field.
        """
        entries = self._load_index()
        results = []
        for entry in entries:
            if age_min is not None and entry.age < age_min:
                continue
            if age_max is not None and entry.age > age_max:
                continue
            if gender is not None and entry.gender != gender:
                continue
            if city_tier is not None and entry.city_tier != city_tier:
                continue
            if domain is not None and entry.domain != domain:
                continue
            results.append(entry)
        return results

    def list_all(self) -> list[RegistryEntry]:
        """Return all RegistryEntry objects from the index."""
        return self._load_index()

    def sync_from_json(self, cohort_json_path: str | Path) -> list[RegistryEntry]:
        """Import personas from a JSON file (list of PersonaRecord dicts).

        The file should contain a JSON array of PersonaRecord-compatible dicts.
        Each is parsed, added to the registry, and a RegistryEntry is returned.

        Returns list of RegistryEntry for all successfully added personas.
        """
        raw = json.loads(Path(cohort_json_path).read_text())
        added: list[RegistryEntry] = []
        for d in raw:
            persona = PersonaRecord.model_validate(d)
            entry = self.add(persona)
            added.append(entry)
        return added
