"""src/social/network_builder.py — Social network topology constructors.

Builds SocialNetwork objects from a list of persona IDs.
No LLM calls. Deterministic (seeded random for RANDOM_ENCOUNTER).
"""
from __future__ import annotations

import random
from itertools import combinations

from src.social.schema import NetworkTopology, SocialNetwork, SocialNetworkEdge


def build_full_mesh(persona_ids: list[str]) -> SocialNetwork:
    """Build a fully-connected bidirectional network.

    Every persona is connected to every other persona.
    Edge type: "peer", weight: 1.0.
    For N personas: N*(N-1) directed edges total (both directions for each pair).

    If len(persona_ids) < 2: returns SocialNetwork with empty edges.
    """
    edges = []
    for a, b in combinations(persona_ids, 2):
        edges.append(SocialNetworkEdge(source_id=a, target_id=b))
        edges.append(SocialNetworkEdge(source_id=b, target_id=a))
    return SocialNetwork(topology=NetworkTopology.FULL_MESH, edges=edges)


def build_random_encounter(
    persona_ids: list[str],
    k: int = 2,
    seed: int | None = None,
) -> SocialNetwork:
    """Build a random encounter network.

    Each persona is paired with k random others (no self-loops, no duplicates).
    Edge direction: source → target (one-directional per sampling).
    Edge type: "peer", weight: 1.0.

    Parameters
    ----------
    persona_ids: list of persona IDs
    k:          number of random partners per persona (default: 2)
    seed:       random seed for reproducibility (default: None)

    If k >= len(persona_ids): k = max(1, len(persona_ids) - 1) to avoid loops.
    If len(persona_ids) < 2: returns empty edges.
    """
    if len(persona_ids) < 2:
        return SocialNetwork(topology=NetworkTopology.RANDOM_ENCOUNTER, edges=[])
    rng = random.Random(seed)
    k = min(k, len(persona_ids) - 1)
    edges = []
    seen: set[tuple[str, str]] = set()
    for source in persona_ids:
        others = [p for p in persona_ids if p != source]
        partners = rng.sample(others, min(k, len(others)))
        for target in partners:
            pair = (source, target)
            if pair not in seen:
                seen.add(pair)
                edges.append(SocialNetworkEdge(source_id=source, target_id=target))
    return SocialNetwork(topology=NetworkTopology.RANDOM_ENCOUNTER, edges=edges)


def build_directed_graph(
    edges: list[tuple[str, str, str, float]],
) -> SocialNetwork:
    """Build a directed graph from explicit edge tuples.

    Each tuple is (source_id, target_id, edge_type, weight).
    edge_type must be one of: "peer", "authority", "family", "influencer".

    This constructor is used when the caller specifies explicit social relationships.
    """
    built_edges = [
        SocialNetworkEdge(source_id=s, target_id=t, edge_type=et, weight=w)
        for s, t, et, w in edges
    ]
    return SocialNetwork(topology=NetworkTopology.DIRECTED_GRAPH, edges=built_edges)
