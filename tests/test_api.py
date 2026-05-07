"""Tests for the Simulatte Persona Generator FastAPI microservice.

Uses FastAPI's TestClient (backed by httpx) for synchronous in-process testing.
_run_generation is mocked to avoid live LLM calls.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

# Minimal envelope dict returned by the mock
MINIMAL_ENVELOPE = {
    "cohort_id": "test-001",
    "domain": "cpg",
    "personas": [],
    "calibration_state": "uncalibrated",
    "created_at": "2026-01-01T00:00:00",
    "icp_spec": {},
}


def test_health_returns_200():
    """GET /health should return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_generate_returns_cohort_id():
    """POST /generate should return a cohort_id when _run_generation succeeds."""
    with patch(
        "src.api.main._run_generation",
        new=AsyncMock(return_value=MINIMAL_ENVELOPE),
    ):
        response = client.post(
            "/generate",
            json={"count": 1, "domain": "cpg", "mode": "quick"},
        )
    assert response.status_code == 200
    body = response.json()
    assert "cohort_id" in body
    assert isinstance(body["cohort_id"], str)
    assert len(body["cohort_id"]) > 0
    assert "persona_count" in body
    assert "cohort" in body


def test_generate_invalid_domain_returns_error():
    """POST /generate with empty domain should return 422."""
    response = client.post(
        "/generate",
        json={"count": 1, "domain": "", "mode": "quick"},
    )
    assert response.status_code == 422


def test_report_missing_cohort_returns_404():
    """GET /report/{cohort_id} for a non-existent cohort_id should return 404."""
    response = client.get("/report/nonexistent-cohort-xyz")
    assert response.status_code == 404


def test_simulate_missing_cohort_returns_404():
    """POST /simulate for a non-existent cohort_id should return 404."""
    response = client.post(
        "/simulate",
        json={
            "cohort_id": "nonexistent-cohort-xyz",
            "scenario": {"stimuli": [], "decision_scenario": None},
            "rounds": 1,
        },
    )
    assert response.status_code == 404


def test_simulate_engine_compat_happy_path():
    """POST /simulate (engine compat: question + options) returns headline + distribution."""
    cohort = {
        "cohort_id": "compat-001",
        "personas": [
            {
                "persona_id": f"p{i}",
                "demographic_anchor": {"name": f"Persona {i}", "age": 30 + i},
                "first_person_narrative": "I value sustainable products.",
            }
            for i in range(5)
        ],
    }
    qna_result = {
        "ok": True,
        "headline": "80% of 5 personas chose \"Yes\"",
        "confidence_score": 0.8,
        "strategic_implication": None,
        "distribution": [
            {"option_id": "yes", "option_name": "Yes", "count": 4, "percentage": 80.0},
            {"option_id": "no", "option_name": "No", "count": 1, "percentage": 20.0},
        ],
        "persona_responses": [
            {"persona_id": "p0", "persona_name": "Persona 0", "option_id": "yes", "rationale": "..."},
        ],
    }
    with patch("src.api.main.load_cohort", return_value=cohort), \
         patch("src.api.simulate_qna.run_qna_simulation", new=AsyncMock(return_value=qna_result)):
        response = client.post(
            "/simulate",
            json={
                "cohort_id": "compat-001",
                "simulation_name": "test",
                "question": "Would you buy this?",
                "context": "A new eco-friendly product.",
                "options": [{"id": "yes", "name": "Yes"}, {"id": "no", "name": "No"}],
                "n_personas": 5,
            },
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["headline"].startswith("80%")
    assert body["confidence_score"] == 0.8
    assert len(body["distribution"]) == 2
    assert body["distribution"][0]["option_id"] == "yes"


def test_simulate_engine_compat_all_failures_returns_502():
    """If every persona Q&A fails, /simulate returns 502."""
    cohort = {
        "cohort_id": "compat-002",
        "personas": [{"persona_id": "p0", "demographic_anchor": {"name": "X"}}],
    }
    failed = {
        "ok": False,
        "error": "all persona Q&A calls failed",
        "headline": None,
        "confidence_score": 0.0,
        "distribution": [],
        "persona_responses": [],
    }
    with patch("src.api.main.load_cohort", return_value=cohort), \
         patch("src.api.simulate_qna.run_qna_simulation", new=AsyncMock(return_value=failed)):
        response = client.post(
            "/simulate",
            json={
                "cohort_id": "compat-002",
                "question": "?",
                "options": [{"id": "yes", "name": "Yes"}],
                "n_personas": 1,
            },
        )
    assert response.status_code == 502


def test_simulate_engine_compat_missing_cohort_returns_404():
    """Engine-shape /simulate against unknown cohort still 404s."""
    response = client.post(
        "/simulate",
        json={
            "cohort_id": "nonexistent-engine-xyz",
            "question": "?",
            "options": [{"id": "yes", "name": "Yes"}],
            "n_personas": 1,
        },
    )
    assert response.status_code == 404


def test_survey_missing_cohort_returns_404():
    """POST /survey for a non-existent cohort_id should return 404."""
    response = client.post(
        "/survey",
        json={
            "cohort_id": "nonexistent-cohort-xyz",
            "questions": ["What do you think about X?"],
        },
    )
    assert response.status_code == 404
