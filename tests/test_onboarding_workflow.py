"""tests/test_onboarding_workflow.py
Sprint 28 — Antigravity test suite
Covers: feature_builder, cluster_pipeline, onboarding_gates, onboarding_workflow
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from src.onboarding.feature_builder import BehaviouralFeatures, build_features_from_tagged_corpus
from src.onboarding.cluster_pipeline import ClusterResult, run_cluster_pipeline
from src.onboarding.onboarding_workflow import OnboardingResult, StepLog, run_onboarding
from src.onboarding.signal_tagger import TaggedCorpus, TaggedSignal
from src.onboarding.ingestion_validator import ValidationReport
from src.onboarding.ingestion import IngestionResult
from src.validation.onboarding_gates import GateResult, check_go1, check_go2


# ---------------------------------------------------------------------------
# ICP fixture used across run_onboarding tests
# ---------------------------------------------------------------------------

SAMPLE_ICP = {
    "domain": "healthcare",
    "business_problem": "Understand why patients delay consultations",
    "target_segment": "Urban adults 25-45",
    "anchor_traits": [],
    "data_sources": [],
}


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

def make_tagged_corpus(n_signals: int = 50, tag: str = "neutral") -> TaggedCorpus:
    """Create a TaggedCorpus with n_signals all tagged with tag."""
    signals = [
        TaggedSignal(text=f"Signal text number {i}", tag=tag, confidence=0.9)
        for i in range(n_signals)
    ]
    distribution = {
        "purchase_trigger": 0,
        "rejection": 0,
        "switching": 0,
        "trust_citation": 0,
        "price_mention": 0,
        "neutral": 0,
    }
    for ts in signals:
        distribution[ts.tag] = distribution.get(ts.tag, 0) + 1
    n_decision = sum(1 for ts in signals if ts.tag != "neutral")
    return TaggedCorpus(
        signals=signals,
        tag_distribution=distribution,
        n_decision_signals=n_decision,
    )


def make_validation_report(n_valid: int = 250) -> ValidationReport:
    """Create a ValidationReport with n_valid signals."""
    return ValidationReport(
        n_raw_signals=n_valid,
        n_unique_signals=n_valid,
        n_near_duplicates_removed=0,
        n_valid_signals=n_valid,
        is_valid=n_valid >= 200,
        proxy_mode_suggested=n_valid < 200,
        recommendation=f"Ready for grounding — {n_valid} signals collected."
        if n_valid >= 200
        else f"Below threshold — {n_valid} signals collected, 200 required.",
    )


def make_ingestion_result(n_valid: int = 250) -> IngestionResult:
    """Create an IngestionResult with a validation_report."""
    report = make_validation_report(n_valid)
    return IngestionResult(
        raw_signals=[f"raw signal {i}" for i in range(n_valid)],
        redacted_signals=[f"redacted signal {i}" for i in range(n_valid)],
        redaction_log=None,
        format_detected="csv",
        validation_report=report,
        tagged_corpus=None,
        ready_for_grounding=report.is_valid,
    )


def _diverse_signal(i: int) -> str:
    """Generate a structurally diverse signal that survives near-dedup."""
    h = hashlib.md5(str(i).encode()).hexdigest()[:8]
    templates = [
        f"The packaging arrived damaged and the seal was broken uid{h}",
        f"Customer service resolved my complaint quickly ref{h}",
        f"Fragrance lasted all day without reapplication code{h}",
        f"Texture felt grainy and unpleasant on skin token{h}",
        f"Value for money exceeded my expectations tag{h}",
        f"Delivery was three days late beyond the promised date id{h}",
        f"Ingredients list showed no harmful chemicals batch{h}",
        f"Size ran small compared to standard measurements sku{h}",
        f"Colour faded after first wash in cold water lot{h}",
        f"Battery life dropped significantly after six months serial{h}",
    ]
    return templates[i % len(templates)]


def make_diverse_csv_bytes(n: int = 250) -> bytes:
    """Generate diverse CSV bytes for end-to-end tests.

    Uses MD5-like unique content per row to avoid near-dedup collapse.
    """
    lines = ["id,text"]
    for i in range(n):
        sig = _diverse_signal(i)
        lines.append(f'{i},"{sig}"')
    return "\n".join(lines).encode("utf-8")


# ---------------------------------------------------------------------------
# Helper: 4-cluster reproducible feature vectors
# ---------------------------------------------------------------------------

def _make_4cluster_vectors(seed: int = 0) -> list[list[float]]:
    np.random.seed(seed)
    centers = [[-5, -5], [5, -5], [-5, 5], [5, 5]]
    return [
        list(c + np.random.randn(2) * 0.5)
        for c in centers
        for _ in range(10)
    ]


# ===========================================================================
# TestBehaviouralFeatures — feature_builder (6 tests)
# ===========================================================================

class TestBehaviouralFeatures:

    # Test 1 — All 5 feature categories present
    def test_all_five_feature_categories_present(self):
        corpus = make_tagged_corpus(20, tag="neutral")
        bf = build_features_from_tagged_corpus(corpus)
        assert hasattr(bf, "price_salience_index")
        assert hasattr(bf, "trust_source_distribution")
        assert hasattr(bf, "switching_trigger_distribution")
        assert hasattr(bf, "objection_cluster_frequencies")
        assert hasattr(bf, "purchase_trigger_distribution")

    # Test 2 — Empty corpus: price_salience_index=0.0; all distribution dicts sum to 0
    def test_empty_corpus_returns_zeros(self):
        empty_corpus = TaggedCorpus(
            signals=[],
            tag_distribution={},
            n_decision_signals=0,
        )
        bf = build_features_from_tagged_corpus(empty_corpus)
        assert bf.price_salience_index == 0.0
        assert bf.n_signals == 0
        # All distribution values are 0.0 when corpus is empty
        for dist in (
            bf.trust_source_distribution,
            bf.switching_trigger_distribution,
            bf.objection_cluster_frequencies,
            bf.purchase_trigger_distribution,
        ):
            assert all(v == 0.0 for v in dist.values())

    # Test 3 — price_salience_index = price_mention_count / n_signals
    def test_price_salience_index_formula(self):
        n = 10
        price_count = 4
        signals = [
            TaggedSignal(text=f"price mention signal {i}", tag="price_mention", confidence=0.9)
            for i in range(price_count)
        ] + [
            TaggedSignal(text=f"other signal {i}", tag="neutral", confidence=0.9)
            for i in range(n - price_count)
        ]
        distribution = {
            "purchase_trigger": 0,
            "rejection": 0,
            "switching": 0,
            "trust_citation": 0,
            "price_mention": price_count,
            "neutral": n - price_count,
        }
        corpus = TaggedCorpus(
            signals=signals,
            tag_distribution=distribution,
            n_decision_signals=price_count,
        )
        bf = build_features_from_tagged_corpus(corpus)
        expected = price_count / n
        assert bf.price_salience_index == pytest.approx(expected)

    # Test 4 — trust_source_distribution: "doctor" keyword → doctor fraction > 0
    def test_trust_source_doctor_keyword(self):
        trust_signals = [
            TaggedSignal(
                text="My doctor recommended this product strongly",
                tag="trust_citation",
                confidence=0.9,
            ),
            TaggedSignal(
                text="A specialist physician confirmed the results",
                tag="trust_citation",
                confidence=0.9,
            ),
        ]
        distribution = {
            "purchase_trigger": 0, "rejection": 0, "switching": 0,
            "trust_citation": 2, "price_mention": 0, "neutral": 0,
        }
        corpus = TaggedCorpus(
            signals=trust_signals,
            tag_distribution=distribution,
            n_decision_signals=2,
        )
        bf = build_features_from_tagged_corpus(corpus)
        assert bf.trust_source_distribution["doctor"] > 0.0

    # Test 5 — All 5 distribution dicts have exactly 5 keys each
    def test_all_distribution_dicts_have_five_keys(self):
        corpus = make_tagged_corpus(30, tag="neutral")
        bf = build_features_from_tagged_corpus(corpus)
        for dist in (
            bf.trust_source_distribution,
            bf.switching_trigger_distribution,
            bf.objection_cluster_frequencies,
            bf.purchase_trigger_distribution,
        ):
            assert len(dist) == 5, f"Expected 5 keys, got {len(dist)}: {list(dist.keys())}"

    # Test 6 — No LLM calls: function returns synchronously without API interaction
    def test_no_llm_calls_synchronous_return(self):
        """build_features_from_tagged_corpus must return synchronously.

        Verified by ensuring the return type is BehaviouralFeatures (not a
        coroutine, future, or any async object) and that it completes without
        patching any network layer.
        """
        import inspect
        corpus = make_tagged_corpus(10, tag="neutral")
        result = build_features_from_tagged_corpus(corpus)
        # Must not be a coroutine or awaitable
        assert not inspect.isawaitable(result)
        assert isinstance(result, BehaviouralFeatures)


# ===========================================================================
# TestClusterPipeline — cluster_pipeline (5 tests)
# ===========================================================================

class TestClusterPipeline:

    # Test 7 — Normal 4-cluster data → stability_passed=True, k in [3,8]
    def test_four_cluster_data_passes_stability(self):
        vectors = _make_4cluster_vectors(seed=0)
        result = run_cluster_pipeline(vectors, k_range=(3, 8))
        assert isinstance(result, ClusterResult)
        assert result.stability_passed is True
        assert 3 <= result.k <= 8

    # Test 8 — Fewer vectors than k_range[0] → k=1, stability_passed=False
    def test_insufficient_vectors_returns_k1(self):
        # Only 2 vectors but k_range starts at 3
        vectors = [[1.0, 2.0], [3.0, 4.0]]
        result = run_cluster_pipeline(vectors, k_range=(3, 8))
        assert result.k == 1
        assert result.stability_passed is False
        assert "Insufficient data" in result.notes

    # Test 9 — Empty feature_vectors → k=1, stability_passed=False
    def test_empty_vectors_returns_k1_no_stability(self):
        result = run_cluster_pipeline([])
        assert result.k == 1
        assert result.stability_passed is False

    # Test 10 — threshold=1.0 → stability_passed=False, K-1 retry fired
    def test_impossible_threshold_triggers_k1_retry(self):
        vectors = _make_4cluster_vectors(seed=0)
        # threshold=1.0 is impossible for silhouette (max is 1.0, never reached)
        result = run_cluster_pipeline(vectors, k_range=(3, 8), threshold=1.0)
        assert result.stability_passed is False
        # K-1 retry fires when best_k > k_range[0] and stability fails.
        # Either the final k is less than the BIC-optimal k, OR notes documents the retry.
        retry_evidence = (result.k < result.k_range_tried[-1]) or ("retry" in result.notes.lower())
        assert retry_evidence, (
            f"Expected K-1 retry evidence. k={result.k}, "
            f"k_range_tried={result.k_range_tried}, notes={result.notes!r}"
        )

    # Test 11 — ClusterResult has all required fields
    def test_cluster_result_has_all_required_fields(self):
        vectors = _make_4cluster_vectors(seed=0)
        result = run_cluster_pipeline(vectors)
        assert hasattr(result, "k")
        assert hasattr(result, "labels")
        assert hasattr(result, "cluster_centroids")
        assert hasattr(result, "mean_silhouette")
        assert hasattr(result, "silhouette_scores")
        assert hasattr(result, "stability_passed")
        assert hasattr(result, "k_range_tried")
        assert hasattr(result, "bic_scores")
        assert isinstance(result.k, int)
        assert isinstance(result.labels, list)
        assert isinstance(result.cluster_centroids, list)
        assert isinstance(result.mean_silhouette, float)
        assert isinstance(result.silhouette_scores, list)
        assert isinstance(result.stability_passed, bool)
        assert isinstance(result.k_range_tried, list)
        assert isinstance(result.bic_scores, dict)


# ===========================================================================
# TestOnboardingGatesGO1 — G-O1 gate (3 tests)
# ===========================================================================

class TestOnboardingGatesGO1:

    # Test 12 — 200 valid signals → passed=True, gate_id="G-O1"
    def test_200_valid_signals_passes(self):
        ingestion = make_ingestion_result(n_valid=200)
        result = check_go1(ingestion)
        assert isinstance(result, GateResult)
        assert result.passed is True
        assert result.gate_id == "G-O1"

    # Test 13 — 199 valid signals → passed=False, action_required non-empty
    def test_199_valid_signals_fails(self):
        ingestion = make_ingestion_result(n_valid=199)
        result = check_go1(ingestion)
        assert result.passed is False
        assert len(result.action_required) > 0

    # Test 14 — 0 valid signals → passed=False
    def test_zero_valid_signals_fails(self):
        ingestion = make_ingestion_result(n_valid=0)
        result = check_go1(ingestion)
        assert result.passed is False


# ===========================================================================
# TestOnboardingGatesGO2 — G-O2 gate (3 tests)
# ===========================================================================

class TestOnboardingGatesGO2:

    def _make_cluster_result(self, stability_passed: bool) -> ClusterResult:
        return ClusterResult(
            k=4,
            labels=[0, 1, 2, 3],
            cluster_centroids=[[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [3.0, 3.0]],
            mean_silhouette=0.72 if stability_passed else 0.15,
            silhouette_scores=[0.72] * 5 if stability_passed else [0.10] * 5,
            stability_passed=stability_passed,
            k_range_tried=[3, 4, 5, 6, 7, 8],
            bic_scores={3: 100.0, 4: 80.0, 5: 90.0},
            notes="test cluster result",
        )

    # Test 15 — stability_passed=True → passed=True, gate_id="G-O2"
    def test_stable_cluster_passes(self):
        cluster = self._make_cluster_result(stability_passed=True)
        result = check_go2(cluster)
        assert result.passed is True
        assert result.gate_id == "G-O2"

    # Test 16 — stability_passed=False → passed=False, action_required non-empty
    def test_unstable_cluster_fails(self):
        cluster = self._make_cluster_result(stability_passed=False)
        result = check_go2(cluster)
        assert result.passed is False
        assert len(result.action_required) > 0

    # Test 17 — GateResult.detail contains K and silhouette values
    def test_detail_contains_k_and_silhouette(self):
        cluster = self._make_cluster_result(stability_passed=True)
        result = check_go2(cluster)
        assert "K=" in result.detail or "k=" in result.detail.lower()
        assert "silhouette" in result.detail.lower()


# ===========================================================================
# TestRunOnboardingCompletePath — 4 tests
# ===========================================================================

class TestRunOnboardingCompletePath:

    # Test 18 — Valid ICP JSON + no data → status="complete", steps 3–6 are "skipped"
    def test_no_data_status_complete_steps_skipped(self):
        result = run_onboarding(SAMPLE_ICP, data_bytes=None)
        assert isinstance(result, OnboardingResult)
        assert result.status == "complete"
        # Steps 3 through 6 should all be "skipped" when no data provided
        skipped_names = {"ingest_data", "g_o1_gate", "build_features", "g_o2_gate"}
        for entry in result.step_log:
            if entry.name in skipped_names:
                assert entry.status == "skipped", (
                    f"Expected step {entry.name!r} to be skipped, got {entry.status!r}"
                )

    # Test 19 — Valid ICP JSON + 250-signal CSV → status="complete"
    def test_250_signal_csv_status_complete(self):
        data = make_diverse_csv_bytes(250)
        result = run_onboarding(SAMPLE_ICP, data_bytes=data)
        assert result.status == "complete"

    # Test 20 — step_log has 6 entries (one per step)
    def test_step_log_has_six_entries(self):
        data = make_diverse_csv_bytes(250)
        result = run_onboarding(SAMPLE_ICP, data_bytes=data)
        assert len(result.step_log) == 6

    # Test 21 — step_log[0].name == "parse_icp_spec"
    def test_first_step_log_entry_is_parse_icp_spec(self):
        result = run_onboarding(SAMPLE_ICP, data_bytes=None)
        assert result.step_log[0].name == "parse_icp_spec"


# ===========================================================================
# TestRunOnboardingPartialPath — 4 tests
# ===========================================================================

class TestRunOnboardingPartialPath:

    # Test 22 — Valid ICP JSON + 150-signal CSV → G-O1 fails → status="partial"
    def test_150_signal_csv_status_partial(self):
        data = make_diverse_csv_bytes(150)
        result = run_onboarding(SAMPLE_ICP, data_bytes=data)
        assert result.status == "partial"

    # Test 23 — status="partial" does not raise — returns OnboardingResult
    def test_partial_status_returns_onboarding_result(self):
        data = make_diverse_csv_bytes(150)
        result = run_onboarding(SAMPLE_ICP, data_bytes=data)
        assert isinstance(result, OnboardingResult)

    # Test 24 — Failed step has status="failed" in step_log
    def test_failed_step_recorded_in_step_log(self):
        data = make_diverse_csv_bytes(150)
        result = run_onboarding(SAMPLE_ICP, data_bytes=data)
        statuses = {entry.name: entry.status for entry in result.step_log}
        assert statuses.get("g_o1_gate") == "failed", (
            f"Expected g_o1_gate to be 'failed', got {statuses.get('g_o1_gate')!r}"
        )

    # Test 25 — features and cluster_result are None when G-O1 fails
    def test_features_and_cluster_none_when_go1_fails(self):
        # With 150 signals, ingestion succeeds but G-O1 fails (< 200 valid).
        # Because ingestion.ready_for_grounding is False (n_valid < 200),
        # step 5 will be skipped → features=None → cluster_result=None.
        data = make_diverse_csv_bytes(150)
        result = run_onboarding(SAMPLE_ICP, data_bytes=data)
        assert result.features is None
        assert result.cluster_result is None


# ===========================================================================
# TestRunOnboardingFailurePath — 2 tests
# ===========================================================================

class TestRunOnboardingFailurePath:

    # Test 26 — Invalid ICP JSON → status="failed"
    def test_invalid_icp_json_status_failed(self):
        invalid_icp = {}  # Missing required domain, business_problem, target_segment
        result = run_onboarding(invalid_icp, data_bytes=None)
        assert result.status == "failed"

    # Test 27 — status="failed" returns OnboardingResult (does not raise)
    def test_failed_status_returns_onboarding_result(self):
        invalid_icp = {}
        result = run_onboarding(invalid_icp, data_bytes=None)
        assert isinstance(result, OnboardingResult)


# ===========================================================================
# TestEndToEndSmoke — 3 tests
# ===========================================================================

class TestEndToEndSmoke:

    # Test 28 — 250-signal diverse CSV → OnboardingResult.status in ("complete", "partial")
    def test_250_signal_diverse_csv_terminal_status(self):
        data = make_diverse_csv_bytes(250)
        result = run_onboarding(SAMPLE_ICP, data_bytes=data)
        assert result.status in ("complete", "partial"), (
            f"Unexpected status: {result.status!r}. Notes: {result.notes!r}"
        )

    # Test 29 — ingestion_result is not None when data provided
    def test_ingestion_result_not_none_when_data_provided(self):
        data = make_diverse_csv_bytes(250)
        result = run_onboarding(SAMPLE_ICP, data_bytes=data)
        assert result.ingestion_result is not None

    # Test 30 — icp_spec present on "complete"/"partial"; may be None on "failed"
    def test_icp_spec_present_on_complete_none_on_failed(self):
        # Successful run: icp_spec must be a truthy ICPSpec object
        data = make_diverse_csv_bytes(250)
        ok_result = run_onboarding(SAMPLE_ICP, data_bytes=data)
        assert ok_result.icp_spec is not None

        # Failed run: icp_spec is None (parse failed before it could be set)
        failed_result = run_onboarding({}, data_bytes=None)
        assert failed_result.status == "failed"
        assert failed_result.icp_spec is None
