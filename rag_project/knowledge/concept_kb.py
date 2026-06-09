"""Bridge the authoritative S01–S21 concept knowledge base into rag_project.

Loads the badminton_forehand_clear_RAG_package: concept chunks (data/chunks.jsonl),
the source catalog (badminton_forehand_clear_sources.csv), and the legacy
crosswalk (source_id_crosswalk.csv). Exposes the concept chunks as the primary,
evidence-layered retrieval corpus and converts them to EvidenceChunk objects for
the diagnosis report. See INTEGRATION.md steps 1/2/5.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rag_project.knowledge.evidence_index import EvidenceChunk

# rag_project/ -> BadmintonRAG/ -> package
_RAG_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RAG_ROOT.parent
PACKAGE_DIR = _REPO_ROOT / "badminton_forehand_clear_RAG_package"
CHUNKS_PATH = PACKAGE_DIR / "data" / "chunks.jsonl"
CATALOG_PATH = PACKAGE_DIR / "badminton_forehand_clear_sources.csv"
CROSSWALK_PATH = PACKAGE_DIR / "source_id_crosswalk.csv"

# Chinese labels for the coarse chunk evidence layer (KB §8.1/§8.2), shown to users.
EVIDENCE_LAYER_LABEL_ZH = {
    "coaching_direct_clear": "直接高远球证据（教练/教学）",
    "peer_reviewed_direct_clear": "直接高远球证据（同行评审）",
    "overhead_multi_stroke": "正手头顶多击球证据（含高远球）",
    "skill_level_overhead": "头顶正手通用（技能水平）",
    "review": "综述/文献导航",
    "smash_analogy": "杀球类比证据",
    "emg_smash_analogy": "杀球 EMG 类比证据",
    "msk_methodological": "EMG+肌骨方法学（杀球类比）",
    "mixed_direct_and_analogy": "混合证据（直接+类比）",
    "dataset": "数据集/方法",
    "injury_review": "伤病/安全背景",
    "implementation": "实现/工程说明",
}

# Layers treated as direct-clear for §10.2 evidence boost / ranking.
DIRECT_CLEAR_LAYERS = {"coaching_direct_clear", "peer_reviewed_direct_clear", "overhead_multi_stroke"}
ANALOGY_LAYERS = {"smash_analogy", "emg_smash_analogy", "msk_methodological"}


@dataclass(frozen=True)
class CrossWalk:
    package_to_legacy: dict[str, str]
    legacy_to_package: dict[str, str]

    def to_package(self, source_id: str) -> str:
        """Translate a legacy string id to its [Sxx] package id; pass through if already Sxx/unknown."""
        if source_id in self.package_to_legacy:
            return source_id
        return self.legacy_to_package.get(source_id, source_id)


@lru_cache(maxsize=1)
def load_crosswalk() -> CrossWalk:
    p2l: dict[str, str] = {}
    l2p: dict[str, str] = {}
    if CROSSWALK_PATH.exists():
        for row in csv.DictReader(CROSSWALK_PATH.open(encoding="utf-8")):
            pkg = (row.get("package_id") or "").strip()
            legacy = (row.get("legacy_id") or "").strip()
            if pkg:
                p2l[pkg] = legacy
                if legacy:
                    l2p[legacy] = pkg
    return CrossWalk(package_to_legacy=p2l, legacy_to_package=l2p)


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, dict[str, str]]:
    catalog: dict[str, dict[str, str]] = {}
    if CATALOG_PATH.exists():
        for row in csv.DictReader(CATALOG_PATH.open(encoding="utf-8")):
            catalog[row["id"]] = row
    return catalog


@lru_cache(maxsize=1)
def load_concept_chunks() -> tuple[dict[str, object], ...]:
    if not CHUNKS_PATH.exists():
        return ()
    return tuple(json.loads(line) for line in CHUNKS_PATH.read_text(encoding="utf-8").splitlines() if line.strip())


def _title_for(source_ids: list[str], catalog: dict[str, dict[str, str]]) -> str:
    titles = [catalog.get(sid, {}).get("title", sid) for sid in source_ids[:2]]
    return " / ".join(t for t in titles if t)


def concept_chunk_to_evidence(chunk: dict[str, object], score: float = 0.0) -> EvidenceChunk:
    """Map a concept chunk dict to an EvidenceChunk for the diagnosis report."""
    catalog = load_catalog()
    source_ids = [str(s) for s in chunk.get("source_ids", [])]
    primary = source_ids[0] if source_ids else "unknown"
    layer = str(chunk.get("evidence_level", "mechanistic_inference"))
    return EvidenceChunk(
        chunk_id=str(chunk["chunk_id"]),
        source_id=primary,
        title=_title_for(source_ids, catalog),
        source_class=f"concept_kb:{layer}",
        artifact_path=str(CHUNKS_PATH),
        text=str(chunk.get("text", "")),
        token_count=len(str(chunk.get("text", ""))),
        evidence_level=layer,
        score=round(float(score), 4),  # coerce numpy float32/64 -> python float for JSON safety
        source_ids=tuple(source_ids),
    )


def evidence_layer_label(layer: str) -> str:
    return EVIDENCE_LAYER_LABEL_ZH.get(layer, layer)


def cite_label(chunk_or_evidence) -> str:
    """Render a `[S05][S08]` style citation with the Chinese evidence-layer label.

    Accepts an EvidenceChunk or a concept chunk dict. Falls back to legacy id via crosswalk.
    """
    if isinstance(chunk_or_evidence, EvidenceChunk):
        sids = list(chunk_or_evidence.source_ids) or [load_crosswalk().to_package(chunk_or_evidence.source_id)]
        layer = chunk_or_evidence.evidence_level
    else:
        sids = [str(s) for s in chunk_or_evidence.get("source_ids", [])]
        layer = str(chunk_or_evidence.get("evidence_level", ""))
    cites = "".join(f"[{s}]" for s in sids)
    label = evidence_layer_label(layer)
    return f"{cites}（{label}）" if label else cites
