"""tests/test_social/test_network_builder.py — Sprint SA network builder tests.

Tests for src/social/network_builder.py: full mesh, random encounter,
and directed graph constructors.
"""
from __future__ import annotations

import pytest

from src.social.network_builder import (
    build_directed_graph,
    build_full_mesh,
    build_random_encounter,
)
from src.social.schema import NetworkTopology


# ---------------------------------------------------------------------------
# build_full_mesh
# ---------------------------------------------------------------------------

def test_full_mesh_2_personas_produces_2_edges():
    """2 personas → 2 directed edges (both directions for the single pair)."""
    net = build_full_mesh(["p-001", "p-002"])
    assert len(net.edges) == 2


def test_full_mesh_3_personas_produces_6_edges():
    """3 personas → 3 pairs × 2 directions = 6 directed edges."""
    net = build_full_mesh(["p-001", "p-002", "p-003"])
    assert len(net.edges) == 6


def test_full_mesh_1_persona_produces_0_edges():
    """1 persona → no pairs → 0 edges."""
    net = build_full_mesh(["p-001"])
    assert len(net.edges) == 0


def test_full_mesh_empty_list_produces_0_edges():
    net = build_full_mesh([])
    assert len(net.edges) == 0


def test_full_mesh_no_self_loops():
    ids = ["p-001", "p-002", "p-003", "p-004"]
    net = build_full_mesh(ids)
    for edge in net.edges:
        assert edge.source_id != edge.target_id, (
            f"Self-loop detected: {edge.source_id} → {edge.target_id}"
        )


def test_full_mesh_topology_label():
    net = build_full_mesh(["p-001", "p-002"])
    assert net.topology == NetworkTopology.FULL_MESH


def test_full_mesh_n_personas_edge_count():
    """Formula: N*(N-1) edges for N personas."""
    for n in range(2, 7):
        ids = [f"p-{i:03d}" for i in range(n)]
        net = build_full_mesh(ids)
        assert len(net.edges) == n * (n - 1), (
            f"Expected {n*(n-1)} edges for {n} personas, got {len(net.edges)}"
        )


# ---------------------------------------------------------------------------
# build_random_encounter
# ---------------------------------------------------------------------------

def test_random_encounter_no_self_loops():
    ids = [f"p-{i:03d}" for i in range(6)]
    net = build_random_encounter(ids, k=2, seed=42)
    for edge in net.edges:
        assert edge.source_id != edge.target_id, (
            f"Self-loop: {edge.source_id} → {edge.target_id}"
        )


def test_random_encounter_reproducible_with_seed():
    """Same seed produces identical edge lists."""
    ids = [f"p-{i:03d}" for i in range(5)]
    net1 = build_random_encounter(ids, k=2, seed=99)
    net2 = build_random_encounter(ids, k=2, seed=99)
    edges1 = [(e.source_id, e.target_id) for e in net1.edges]
    edges2 = [(e.source_id, e.target_id) for e in net2.edges]
    assert edges1 == edges2


def test_random_encounter_different_seeds_may_differ():
    """Different seeds should (with overwhelming probability) differ."""
    ids = [f"p-{i:03d}" for i in range(8)]
    net1 = build_random_encounter(ids, k=3, seed=1)
    net2 = build_random_encounter(ids, k=3, seed=2)
    edges1 = [(e.source_id, e.target_id) for e in net1.edges]
    edges2 = [(e.source_id, e.target_id) for e in net2.edges]
    # This is almost certainly true for non-trivial inputs
    assert edges1 != edges2


def test_random_encounter_k_capped_at_n_minus_1():
    """When k >= len(personas), k is capped at len(personas) - 1."""
    ids = ["p-001", "p-002", "p-003"]
    # k=10 >> 3 personas, so effective k = 2
    net = build_random_encounter(ids, k=10, seed=7)
    # Each persona should connect to at most 2 others (no self-loops)
    sources = [e.source_id for e in net.edges]
    for pid in ids:
        targets_for_pid = [e.target_id for e in net.edges if e.source_id == pid]
        assert len(targets_for_pid) <= len(ids) - 1


def test_random_encounter_topology_label():
    ids = ["p-001", "p-002", "p-003"]
    net = build_random_encounter(ids, k=1, seed=0)
    assert net.topology == NetworkTopology.RANDOM_ENCOUNTER


def test_random_encounter_1_persona_empty_edges():
    net = build_random_encounter(["p-001"], k=2, seed=0)
    assert len(net.edges) == 0


# ---------------------------------------------------------------------------
# build_directed_graph
# ---------------------------------------------------------------------------

def test_directed_graph_correct_edge_type():
    edges_input = [
        ("p-001", "p-002", "authority", 1.5),
        ("p-003", "p-001", "family", 2.0),
    ]
    net = build_directed_graph(edges_input)
    edge_types = [e.edge_type for e in net.edges]
    assert "authority" in edge_types
    assert "family" in edge_types


def test_directed_graph_correct_weight():
    edges_input = [
        ("p-001", "p-002", "peer", 0.8),
        ("p-002", "p-003", "influencer", 1.2),
    ]
    net = build_directed_graph(edges_input)
    weights = {(e.source_id, e.target_id): e.weight for e in net.edges}
    assert abs(weights[("p-001", "p-002")] - 0.8) < 1e-9
    assert abs(weights[("p-002", "p-003")] - 1.2) < 1e-9


def test_directed_graph_topology_label():
    net = build_directed_graph([("p-001", "p-002", "peer", 1.0)])
    assert net.topology == NetworkTopology.DIRECTED_GRAPH


def test_directed_graph_edge_count_matches_input():
    edges_input = [
        ("p-001", "p-002", "peer", 1.0),
        ("p-002", "p-003", "authority", 1.5),
        ("p-003", "p-001", "family", 0.5),
    ]
    net = build_directed_graph(edges_input)
    assert len(net.edges) == 3


def test_directed_graph_source_target_preserved():
    net = build_directed_graph([("alice", "bob", "influencer", 0.9)])
    assert net.edges[0].source_id == "alice"
    assert net.edges[0].target_id == "bob"
