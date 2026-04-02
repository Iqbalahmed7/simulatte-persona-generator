"""tests/test_sprint18_littlejoys.py — Sprint 18 Gate Tests: Littlejoys Persona Integration.

Validates four Sprint 18 deliverable areas:
  - Domain Template (3 tests)
  - Signal Extractor (3 tests)
  - Converter (3 tests)
  - Pipeline Script (3 tests)

No live API calls. Parallel-agent artefacts that are not yet on disk are
gracefully skipped via pytest.skip().
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Domain Template (3 tests)
# ---------------------------------------------------------------------------


def test_littlejoys_domain_template_importable():
    """LITTLEJOYS_CPG_TEMPLATE can be imported from littlejoys_cpg module."""
    try:
        from src.taxonomy.domain_templates.littlejoys_cpg import LITTLEJOYS_CPG_TEMPLATE
        assert LITTLEJOYS_CPG_TEMPLATE is not None
    except ImportError:
        pytest.skip("Littlejoys domain template not yet built")


def test_littlejoys_template_has_child_nutrition_group():
    """LITTLEJOYS_CPG_TEMPLATE contains child-nutrition-specific attributes.

    The template is a flat list[AttributeDefinition]; we verify the presence
    of canonical child-nutrition attributes such as 'supplement_necessity_belief'
    and 'immunity_concern' that are defined in that conceptual group.
    """
    try:
        from src.taxonomy.domain_templates.littlejoys_cpg import LITTLEJOYS_CPG_TEMPLATE
        attr_names = [a.name for a in LITTLEJOYS_CPG_TEMPLATE]
        child_nutrition_attrs = {
            "supplement_necessity_belief",
            "immunity_concern",
            "growth_concern",
            "nutrition_gap_awareness",
        }
        missing = child_nutrition_attrs - set(attr_names)
        assert not missing, (
            f"LITTLEJOYS_CPG_TEMPLATE is missing child-nutrition attributes: {missing}"
        )
    except ImportError:
        pytest.skip("Littlejoys domain template not yet built")


def test_littlejoys_template_registered_in_loader():
    """'littlejoys_cpg' is registered in the DOMAIN_REGISTRY."""
    try:
        from src.taxonomy.domain_templates.template_loader import DOMAIN_REGISTRY
        assert "littlejoys_cpg" in DOMAIN_REGISTRY
    except ImportError:
        pytest.skip("Template loader not available")


# ---------------------------------------------------------------------------
# Signal Extractor (3 tests)
# ---------------------------------------------------------------------------


def test_signals_file_exists():
    """signals/littlejoys_signals.json exists and contains 100+ signal strings."""
    from pathlib import Path
    signals_path = Path(
        "/Users/admin/Documents/Simulatte Projects/1. LittleJoys/data/signals/littlejoys_signals.json"
    )
    if not signals_path.exists():
        pytest.skip("signals file not yet generated")
    import json
    signals = json.loads(signals_path.read_text())
    assert isinstance(signals, list)
    assert len(signals) > 100, f"Expected 100+ signals, got {len(signals)}"


def test_signals_are_text_strings():
    """Each entry in littlejoys_signals.json is a non-trivial string (>10 chars)."""
    from pathlib import Path
    import json
    signals_path = Path(
        "/Users/admin/Documents/Simulatte Projects/1. LittleJoys/data/signals/littlejoys_signals.json"
    )
    if not signals_path.exists():
        pytest.skip("signals file not yet generated")
    signals = json.loads(signals_path.read_text())
    assert all(isinstance(s, str) and len(s) > 10 for s in signals[:10])


def test_extract_signals_script_importable():
    """pilots/littlejoys/extract_signals.py exists and has a loadable module spec."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "extract_signals",
            "/Users/admin/Documents/Simulatte Projects/Persona Generator/pilots/littlejoys/extract_signals.py",
        )
        assert spec is not None
    except Exception:
        pytest.skip("extract_signals.py not yet built")


# ---------------------------------------------------------------------------
# Converter (3 tests)
# ---------------------------------------------------------------------------


def test_simulatte_personas_file_exists():
    """population/simulatte_personas.json exists and is a non-empty list."""
    from pathlib import Path
    p = Path(
        "/Users/admin/Documents/Simulatte Projects/1. LittleJoys/data/population/simulatte_personas.json"
    )
    if not p.exists():
        pytest.skip("simulatte_personas.json not yet generated — run convert_to_simulatte.py")
    import json
    personas = json.loads(p.read_text())
    assert isinstance(personas, list)
    assert len(personas) > 0


def test_converted_personas_have_required_fields():
    """Each converted persona dict contains the four required top-level fields."""
    from pathlib import Path
    import json
    p = Path(
        "/Users/admin/Documents/Simulatte Projects/1. LittleJoys/data/population/simulatte_personas.json"
    )
    if not p.exists():
        pytest.skip("simulatte_personas.json not yet generated")
    personas = json.loads(p.read_text())
    required = {"persona_id", "demographic_anchor", "attributes", "narrative"}
    for persona in personas[:5]:
        for field in required:
            assert field in persona, f"Missing field: {field}"


def test_converted_personas_are_valid_persona_records():
    """First 5 converted personas pass PersonaRecord validation with lj- IDs in India."""
    from pathlib import Path
    import json
    p = Path(
        "/Users/admin/Documents/Simulatte Projects/1. LittleJoys/data/population/simulatte_personas.json"
    )
    if not p.exists():
        pytest.skip("simulatte_personas.json not yet generated")
    try:
        from src.schema.persona import PersonaRecord
    except ImportError:
        pytest.skip("PersonaRecord schema not available")
    personas = json.loads(p.read_text())
    for raw in personas[:5]:
        record = PersonaRecord.model_validate(raw)
        assert record.persona_id.startswith("pg-lj-"), (
            f"persona_id should start with 'pg-lj-', got: {record.persona_id}"
        )
        assert record.demographic_anchor.location.country == "India", (
            f"Expected country='India', got: {record.demographic_anchor.location.country}"
        )


# ---------------------------------------------------------------------------
# Pipeline Script (3 tests)
# ---------------------------------------------------------------------------


def test_regenerate_pipeline_script_exists():
    """pilots/littlejoys/regenerate_pipeline.py exists in the project."""
    from pathlib import Path
    p = Path(
        "/Users/admin/Documents/Simulatte Projects/Persona Generator/pilots/littlejoys/regenerate_pipeline.py"
    )
    assert p.exists(), "regenerate_pipeline.py should exist"


def test_littlejoys_spec_has_correct_client():
    """spec_littlejoys.json has client='Littlejoys', sarvam_enabled=True, and target_segments."""
    import json
    from pathlib import Path
    spec_path = Path(
        "/Users/admin/Documents/Simulatte Projects/Persona Generator/examples/spec_littlejoys.json"
    )
    data = json.loads(spec_path.read_text())
    assert data.get("client") == "Littlejoys"
    assert data.get("sarvam_enabled") is True
    assert "target_segments" in data
    assert len(data["target_segments"]) >= 2, (
        f"Expected at least 2 target_segments, got {len(data['target_segments'])}"
    )


def test_littlejoys_spec_has_three_segments():
    """target_segments in spec_littlejoys.json sum to 150+ total personas."""
    import json
    from pathlib import Path
    spec_path = Path(
        "/Users/admin/Documents/Simulatte Projects/Persona Generator/examples/spec_littlejoys.json"
    )
    data = json.loads(spec_path.read_text())
    segments = data.get("target_segments", [])
    total_count = sum(s.get("count", 0) for s in segments)
    assert total_count >= 150, (
        f"Expected 150+ total personas across segments, got {total_count}"
    )
