"""tests/test_language_gates.py — Sprint 29 language-validation test suite.

Covers:
    src/validation/language_gates.py      — GateStatus, LanguageGateResult,
                                            check_cr1_v, check_cr2_v,
                                            check_cr3_v, check_cr4_v,
                                            O15_BLOCKER_REASON
    src/validation/readiness_report.py    — ReadinessStatus, LanguageReadinessReport,
                                            build_readiness_report
    src/validation/regional_harness.py   — RegionalTestPersona, REGION_LANGUAGE_MAP,
                                            generate_test_fixtures,
                                            check_language_region_validity
    src/validation/language_region_matrix.py — LanguageRegionCompatibility,
                                               LANGUAGE_REGION_MATRIX,
                                               check_language_region,
                                               get_valid_languages_for_region,
                                               get_valid_regions_for_language
"""

import pytest

from src.validation.language_gates import (
    GateStatus,
    LanguageGateResult,
    O15_BLOCKER_REASON,
    check_cr1_v,
    check_cr2_v,
    check_cr3_v,
    check_cr4_v,
)
from src.validation.readiness_report import (
    LanguageReadinessReport,
    ReadinessStatus,
    build_readiness_report,
)
from src.validation.regional_harness import (
    REGION_LANGUAGE_MAP,
    RegionalTestPersona,
    check_language_region_validity,
    generate_test_fixtures,
)
from src.validation.language_region_matrix import (
    LANGUAGE_REGION_MATRIX,
    LanguageRegionCompatibility,
    check_language_region,
    get_valid_languages_for_region,
    get_valid_regions_for_language,
)


# ===========================================================================
# CR1-V — always NOT_RUN (O15 blocker active)
# ===========================================================================

def test_cr1_v_no_evidence_returns_not_run():
    result = check_cr1_v("hindi")
    assert result.status == GateStatus.NOT_RUN


def test_cr1_v_with_evidence_still_returns_not_run():
    result = check_cr1_v("hindi", evidence={"n_personas_tested": 10, "all_passed": True})
    assert result.status == GateStatus.NOT_RUN


def test_cr1_v_with_empty_dict_evidence_returns_not_run():
    result = check_cr1_v("hindi", evidence={})
    assert result.status == GateStatus.NOT_RUN


def test_cr1_v_gate_id():
    result = check_cr1_v("tamil")
    assert result.gate_id == "CR1-V"


def test_cr1_v_detail_contains_o15_blocker_reason():
    result = check_cr1_v("telugu")
    assert O15_BLOCKER_REASON in result.detail


# ===========================================================================
# CR2-V — always NOT_RUN (O15 blocker active)
# ===========================================================================

def test_cr2_v_no_evidence_returns_not_run():
    result = check_cr2_v("marathi")
    assert result.status == GateStatus.NOT_RUN


def test_cr2_v_with_evidence_still_returns_not_run():
    result = check_cr2_v("bengali", evidence={"spot_check_passed": True})
    assert result.status == GateStatus.NOT_RUN


def test_cr2_v_gate_id():
    result = check_cr2_v("kannada")
    assert result.gate_id == "CR2-V"


def test_cr2_v_detail_contains_o15_blocker_reason():
    result = check_cr2_v("gujarati")
    assert O15_BLOCKER_REASON in result.detail


# ===========================================================================
# CR3-V — human evaluator realism gate
# ===========================================================================

def _make_evaluator(name: str, mean_score: float, dimension_scores: list) -> dict:
    return {"name": name, "mean_score": mean_score, "dimension_scores": dimension_scores}


def test_cr3_v_evidence_none_returns_evidence_needed():
    result = check_cr3_v("hindi", evidence=None)
    assert result.status == GateStatus.EVIDENCE_NEEDED


def test_cr3_v_empty_evaluators_list_returns_evidence_needed():
    result = check_cr3_v("hindi", evidence={"evaluators": [], "n_evaluators": 0})
    assert result.status == GateStatus.EVIDENCE_NEEDED


def test_cr3_v_n_evaluators_one_returns_failed():
    ev = _make_evaluator("Priya", 4.5, [4.0, 4.5, 5.0])
    result = check_cr3_v("hindi", evidence={"evaluators": [ev], "n_evaluators": 1})
    assert result.status == GateStatus.FAILED


def test_cr3_v_overall_mean_below_threshold_returns_failed():
    ev1 = _make_evaluator("A", 3.5, [3.5, 3.5, 3.5])
    ev2 = _make_evaluator("B", 3.5, [3.5, 3.5, 3.5])
    result = check_cr3_v("hindi", evidence={"evaluators": [ev1, ev2], "n_evaluators": 2})
    assert result.status == GateStatus.FAILED


def test_cr3_v_dimension_score_below_3_returns_failed():
    ev1 = _make_evaluator("A", 4.5, [4.0, 4.0, 2.5])  # 2.5 triggers failure
    ev2 = _make_evaluator("B", 4.5, [4.0, 4.0, 4.0])
    result = check_cr3_v("hindi", evidence={"evaluators": [ev1, ev2], "n_evaluators": 2})
    assert result.status == GateStatus.FAILED


def test_cr3_v_all_passing_conditions_returns_ready():
    ev1 = _make_evaluator("Ravi", 4.2, [4.0, 4.5, 4.0])
    ev2 = _make_evaluator("Meera", 4.4, [4.5, 4.0, 4.5])
    result = check_cr3_v(
        "hindi",
        evidence={"evaluators": [ev1, ev2], "n_evaluators": 2},
    )
    assert result.status == GateStatus.READY


def test_cr3_v_gate_id():
    result = check_cr3_v("tamil", evidence=None)
    assert result.gate_id == "CR3-V"


# ===========================================================================
# CR4-V — bilingual fidelity gate
# ===========================================================================

def test_cr4_v_evidence_none_returns_evidence_needed():
    result = check_cr4_v("hindi", evidence=None)
    assert result.status == GateStatus.EVIDENCE_NEEDED


def test_cr4_v_pairs_tested_below_5_returns_evidence_needed():
    result = check_cr4_v("hindi", evidence={"pairs_tested": 3, "pairs_confirmed": 3})
    assert result.status == GateStatus.EVIDENCE_NEEDED


def test_cr4_v_pairs_tested_5_confirmed_2_returns_failed():
    result = check_cr4_v("hindi", evidence={"pairs_tested": 5, "pairs_confirmed": 2})
    assert result.status == GateStatus.FAILED


def test_cr4_v_pairs_tested_5_confirmed_4_returns_ready():
    result = check_cr4_v("hindi", evidence={"pairs_tested": 5, "pairs_confirmed": 4})
    assert result.status == GateStatus.READY


def test_cr4_v_pairs_tested_5_confirmed_5_returns_ready():
    result = check_cr4_v("hindi", evidence={"pairs_tested": 5, "pairs_confirmed": 5})
    assert result.status == GateStatus.READY


def test_cr4_v_gate_id():
    result = check_cr4_v("tamil", evidence=None)
    assert result.gate_id == "CR4-V"


# ===========================================================================
# build_readiness_report — overall status derivation
# ===========================================================================

def _make_gate_result(gate_id: str, language: str, status: GateStatus) -> LanguageGateResult:
    return LanguageGateResult(
        gate_id=gate_id,
        language=language,
        status=status,
        detail=f"stub detail for {gate_id}",
    )


def _all_ready_results(language: str = "hindi") -> tuple:
    return (
        _make_gate_result("CR1-V", language, GateStatus.READY),
        _make_gate_result("CR2-V", language, GateStatus.READY),
        _make_gate_result("CR3-V", language, GateStatus.READY),
        _make_gate_result("CR4-V", language, GateStatus.READY),
    )


def test_build_report_any_not_run_gives_blocked_status():
    cr1 = check_cr1_v("hindi")                       # always NOT_RUN
    cr2 = check_cr2_v("hindi")                       # always NOT_RUN
    cr3 = _make_gate_result("CR3-V", "hindi", GateStatus.EVIDENCE_NEEDED)
    cr4 = _make_gate_result("CR4-V", "hindi", GateStatus.EVIDENCE_NEEDED)
    report = build_readiness_report("hindi", cr1, cr2, cr3, cr4)
    assert report.status == ReadinessStatus.BLOCKED


def test_build_report_all_evidence_needed_gives_evidence_needed_status():
    cr1 = _make_gate_result("CR1-V", "tamil", GateStatus.EVIDENCE_NEEDED)
    cr2 = _make_gate_result("CR2-V", "tamil", GateStatus.EVIDENCE_NEEDED)
    cr3 = _make_gate_result("CR3-V", "tamil", GateStatus.EVIDENCE_NEEDED)
    cr4 = _make_gate_result("CR4-V", "tamil", GateStatus.EVIDENCE_NEEDED)
    report = build_readiness_report("tamil", cr1, cr2, cr3, cr4)
    assert report.status == ReadinessStatus.EVIDENCE_NEEDED


def test_build_report_all_gates_ready_gives_ready_for_review_status():
    cr1, cr2, cr3, cr4 = _all_ready_results("marathi")
    report = build_readiness_report("marathi", cr1, cr2, cr3, cr4)
    assert report.status == ReadinessStatus.READY_FOR_REVIEW


def test_build_report_tech_lead_sign_off_always_true():
    cr1, cr2, cr3, cr4 = _all_ready_results()
    report = build_readiness_report("hindi", cr1, cr2, cr3, cr4)
    assert report.tech_lead_sign_off_required is True


def test_build_report_tech_lead_sign_off_true_even_when_blocked():
    cr1 = check_cr1_v("hindi")
    cr2 = check_cr2_v("hindi")
    cr3 = _make_gate_result("CR3-V", "hindi", GateStatus.EVIDENCE_NEEDED)
    cr4 = _make_gate_result("CR4-V", "hindi", GateStatus.EVIDENCE_NEEDED)
    report = build_readiness_report("hindi", cr1, cr2, cr3, cr4)
    assert report.tech_lead_sign_off_required is True


def test_build_report_blocking_reasons_populated_from_non_ready_gates():
    cr1 = check_cr1_v("hindi")       # NOT_RUN → detail = O15_BLOCKER_REASON
    cr2 = check_cr2_v("hindi")       # NOT_RUN → detail = O15_BLOCKER_REASON
    cr3 = _make_gate_result("CR3-V", "hindi", GateStatus.EVIDENCE_NEEDED)
    cr4 = _make_gate_result("CR4-V", "hindi", GateStatus.EVIDENCE_NEEDED)
    report = build_readiness_report("hindi", cr1, cr2, cr3, cr4)
    assert len(report.blocking_reasons) == 4
    assert O15_BLOCKER_REASON in report.blocking_reasons


def test_build_report_no_blocking_reasons_when_all_ready():
    cr1, cr2, cr3, cr4 = _all_ready_results()
    report = build_readiness_report("hindi", cr1, cr2, cr3, cr4)
    assert report.blocking_reasons == []


def test_build_report_language_stored_correctly():
    cr1, cr2, cr3, cr4 = _all_ready_results("bengali")
    report = build_readiness_report("bengali", cr1, cr2, cr3, cr4)
    assert report.language == "bengali"


def test_build_report_failed_gate_contributes_to_blocking_reasons():
    cr1 = _make_gate_result("CR1-V", "hindi", GateStatus.EVIDENCE_NEEDED)
    cr2 = _make_gate_result("CR2-V", "hindi", GateStatus.EVIDENCE_NEEDED)
    cr3 = _make_gate_result("CR3-V", "hindi", GateStatus.FAILED)
    cr4 = _make_gate_result("CR4-V", "hindi", GateStatus.EVIDENCE_NEEDED)
    report = build_readiness_report("hindi", cr1, cr2, cr3, cr4)
    assert any("CR3-V" in reason for reason in report.blocking_reasons)


# ===========================================================================
# regional_harness — generate_test_fixtures and check_language_region_validity
# ===========================================================================

def test_generate_test_fixtures_returns_exact_count():
    fixtures = generate_test_fixtures("hindi", "maharashtra", n=5)
    assert len(fixtures) == 5


def test_generate_test_fixtures_default_count_is_10():
    fixtures = generate_test_fixtures("hindi", "maharashtra")
    assert len(fixtures) == 10


def test_generate_test_fixtures_hindi_maharashtra_compatible_true():
    fixtures = generate_test_fixtures("hindi", "maharashtra", n=3)
    assert all(f.expected_language_region_compatible for f in fixtures)


def test_generate_test_fixtures_tamil_maharashtra_compatible_false():
    fixtures = generate_test_fixtures("tamil", "maharashtra", n=3)
    assert all(not f.expected_language_region_compatible for f in fixtures)


def test_generate_test_fixtures_persona_id_format():
    fixtures = generate_test_fixtures("hindi", "delhi", n=3)
    assert fixtures[0].persona_id == "test-hindi-delhi-000"
    assert fixtures[1].persona_id == "test-hindi-delhi-001"
    assert fixtures[2].persona_id == "test-hindi-delhi-002"


def test_generate_test_fixtures_language_and_region_stored():
    fixtures = generate_test_fixtures("tamil", "tamil_nadu", n=1)
    assert fixtures[0].language == "tamil"
    assert fixtures[0].region == "tamil_nadu"


def test_check_language_region_validity_valid_pair_returns_true():
    assert check_language_region_validity("hindi", "maharashtra") is True


def test_check_language_region_validity_invalid_pair_returns_false():
    assert check_language_region_validity("tamil", "maharashtra") is False


def test_check_language_region_validity_unknown_region_returns_false():
    assert check_language_region_validity("hindi", "unknown_region") is False


def test_region_language_map_contains_expected_regions():
    expected_regions = {"maharashtra", "tamil_nadu", "karnataka", "west_bengal", "delhi"}
    assert expected_regions == set(REGION_LANGUAGE_MAP.keys())


# ===========================================================================
# language_region_matrix — check_language_region, get_valid_* helpers
# ===========================================================================

def test_check_language_region_hindi_tamil_nadu_prohibited():
    result = check_language_region("hindi", "tamil_nadu")
    assert result.compatible is False
    assert result.prohibited_combination is True


def test_check_language_region_hindi_delhi_compatible():
    result = check_language_region("hindi", "delhi")
    assert result.compatible is True
    assert result.prohibited_combination is False


def test_check_language_region_iso_code_ta_tamil_nadu_compatible():
    result = check_language_region("ta", "tamil_nadu")
    assert result.compatible is True


def test_check_language_region_full_name_tamil_tamil_nadu_compatible():
    result = check_language_region("tamil", "tamil_nadu")
    assert result.compatible is True


def test_check_language_region_unknown_pairing_not_prohibited():
    result = check_language_region("unknown", "unknown")
    assert result.compatible is False
    assert result.prohibited_combination is False


def test_check_language_region_ta_maharashtra_prohibited():
    result = check_language_region("ta", "maharashtra")
    assert result.compatible is False
    assert result.prohibited_combination is True


def test_check_language_region_region_alias_bengal_resolves():
    result = check_language_region("bn", "bengal")
    assert result.compatible is True


def test_get_valid_languages_for_region_tamil_nadu_contains_ta():
    langs = get_valid_languages_for_region("tamil_nadu")
    assert "ta" in langs


def test_get_valid_languages_for_region_unknown_region_returns_empty():
    langs = get_valid_languages_for_region("nonexistent_region")
    assert langs == []


def test_get_valid_regions_for_language_hindi_contains_delhi():
    regions = get_valid_regions_for_language("hindi")
    assert "delhi" in regions


def test_get_valid_regions_for_language_full_name_resolved():
    regions = get_valid_regions_for_language("hindi")
    assert "maharashtra" in regions


def test_get_valid_regions_for_language_unknown_returns_empty():
    regions = get_valid_regions_for_language("klingon")
    assert regions == []


def test_language_region_matrix_is_nonempty_list():
    assert isinstance(LANGUAGE_REGION_MATRIX, list)
    assert len(LANGUAGE_REGION_MATRIX) > 0


def test_language_region_matrix_all_entries_are_correct_type():
    for entry in LANGUAGE_REGION_MATRIX:
        assert isinstance(entry, LanguageRegionCompatibility)
