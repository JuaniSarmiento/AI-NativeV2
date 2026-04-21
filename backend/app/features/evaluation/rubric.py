"""Rubric loader for the N4 evaluation rubric (Anexo B).

Loads the YAML rubric file at startup and returns a typed RubricConfig
dataclass. If the file is missing, logs a warning and returns hardcoded
defaults so the MetricsEngine never fails due to missing config.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Path is relative to the `backend/` directory (project root for the backend service)
_DEFAULT_RUBRIC_PATH = Path(__file__).resolve().parents[4] / "rubrics" / "n4_anexo_b.yaml"


@dataclass(frozen=True)
class RubricWeights:
    n1_comprehension: float = 0.15
    n2_strategy: float = 0.25
    n3_validation: float = 0.25
    n4_ai_interaction: float = 0.20
    qe: float = 0.15


@dataclass(frozen=True)
class RiskThresholdLevel:
    dependency_score_min: float | None = None
    n4_score_max: float | None = None
    any_n_score_max: float | None = None
    qe_score_max: float | None = None


@dataclass(frozen=True)
class RiskThresholds:
    critical: RiskThresholdLevel = field(
        default_factory=lambda: RiskThresholdLevel(dependency_score_min=0.7, n4_score_max=30)
    )
    high: RiskThresholdLevel = field(
        default_factory=lambda: RiskThresholdLevel(dependency_score_min=0.5, any_n_score_max=20)
    )
    medium: RiskThresholdLevel = field(
        default_factory=lambda: RiskThresholdLevel(any_n_score_max=40, qe_score_max=40)
    )


@dataclass(frozen=True)
class QualityFactorDef:
    events: tuple[str, ...] = field(default_factory=tuple)
    min_engagement_seconds: int = 0
    requires_prior: tuple[str, ...] = field(default_factory=tuple)
    requires_correction: bool = False
    dependency_penalty: float = 0.0


@dataclass(frozen=True)
class QualityFactors:
    n1: QualityFactorDef = field(
        default_factory=lambda: QualityFactorDef(
            events=("reads_problem", "code.snapshot"),
            min_engagement_seconds=10,
        )
    )
    n2: QualityFactorDef = field(
        default_factory=lambda: QualityFactorDef(
            events=("submission.created",),
            requires_prior=("code.run",),
        )
    )
    n3: QualityFactorDef = field(
        default_factory=lambda: QualityFactorDef(
            events=("code.run",),
            requires_correction=True,
        )
    )
    n4: QualityFactorDef = field(
        default_factory=lambda: QualityFactorDef(
            events=("tutor.question_asked",),
            dependency_penalty=0.3,
        )
    )


@dataclass(frozen=True)
class CoherenceConfig:
    """Thresholds for the CoherenceEngine (EPIC-20 Fase C)."""

    external_integration_threshold_lines: int = 50
    code_discourse_keywords_min_match: float = 0.3
    generative_dominance_threshold: float = 0.6


@dataclass(frozen=True)
class QeWeightsConfig:
    """Per-level weights for the Qe composite score (B9)."""

    n1: float = 0.25
    n2: float = 0.25
    n3: float = 0.25
    n4: float = 0.25


@dataclass(frozen=True)
class RubricConfig:
    weights: RubricWeights = field(default_factory=RubricWeights)
    risk_thresholds: RiskThresholds = field(default_factory=RiskThresholds)
    quality_factors: QualityFactors = field(default_factory=QualityFactors)
    coherence: CoherenceConfig = field(default_factory=CoherenceConfig)
    qe_weights: QeWeightsConfig = field(default_factory=QeWeightsConfig)


def _parse_yaml(data: dict) -> RubricConfig:  # type: ignore[type-arg]
    """Parse raw YAML dict into a typed RubricConfig."""
    w = data.get("weights", {})
    weights = RubricWeights(
        n1_comprehension=float(w.get("n1_comprehension", 0.15)),
        n2_strategy=float(w.get("n2_strategy", 0.25)),
        n3_validation=float(w.get("n3_validation", 0.25)),
        n4_ai_interaction=float(w.get("n4_ai_interaction", 0.20)),
        qe=float(w.get("qe", 0.15)),
    )

    rt = data.get("risk_thresholds", {})

    def _level(d: dict) -> RiskThresholdLevel:  # type: ignore[type-arg]
        return RiskThresholdLevel(
            dependency_score_min=float(d["dependency_score_min"]) if "dependency_score_min" in d else None,
            n4_score_max=float(d["n4_score_max"]) if "n4_score_max" in d else None,
            any_n_score_max=float(d["any_n_score_max"]) if "any_n_score_max" in d else None,
            qe_score_max=float(d["qe_score_max"]) if "qe_score_max" in d else None,
        )

    risk_thresholds = RiskThresholds(
        critical=_level(rt.get("critical", {})),
        high=_level(rt.get("high", {})),
        medium=_level(rt.get("medium", {})),
    )

    qf = data.get("quality_factors", {})

    def _qfactor(d: dict) -> QualityFactorDef:  # type: ignore[type-arg]
        return QualityFactorDef(
            events=tuple(d.get("events", [])),
            min_engagement_seconds=int(d.get("min_engagement_seconds", 0)),
            requires_prior=tuple(d.get("requires_prior", [])),
            requires_correction=bool(d.get("requires_correction", False)),
            dependency_penalty=float(d.get("dependency_penalty", 0.0)),
        )

    quality_factors = QualityFactors(
        n1=_qfactor(qf.get("n1", {})),
        n2=_qfactor(qf.get("n2", {})),
        n3=_qfactor(qf.get("n3", {})),
        n4=_qfactor(qf.get("n4", {})),
    )

    coh = data.get("coherence", {})
    coherence = CoherenceConfig(
        external_integration_threshold_lines=int(
            coh.get("external_integration_threshold_lines", 50)
        ),
        code_discourse_keywords_min_match=float(
            coh.get("code_discourse_keywords_min_match", 0.3)
        ),
        generative_dominance_threshold=float(
            coh.get("generative_dominance_threshold", 0.6)
        ),
    )

    qw = data.get("qe_weights", {})
    qe_weights = QeWeightsConfig(
        n1=float(qw.get("n1", 0.25)),
        n2=float(qw.get("n2", 0.25)),
        n3=float(qw.get("n3", 0.25)),
        n4=float(qw.get("n4", 0.25)),
    )

    return RubricConfig(
        weights=weights,
        risk_thresholds=risk_thresholds,
        quality_factors=quality_factors,
        coherence=coherence,
        qe_weights=qe_weights,
    )


def load_rubric(path: Path | None = None) -> RubricConfig:
    """Load the N4 rubric from YAML.

    Falls back to hardcoded defaults if the file is not found or cannot
    be parsed, so the MetricsEngine always has a valid config.

    Args:
        path: Override the default rubric path (useful in tests).

    Returns:
        Parsed RubricConfig dataclass.
    """
    rubric_path = path or _DEFAULT_RUBRIC_PATH

    if not rubric_path.exists():
        logger.warning(
            "Rubric file not found — using hardcoded defaults",
            extra={"path": str(rubric_path)},
        )
        return RubricConfig()

    try:
        import yaml  # type: ignore[import-untyped]

        with rubric_path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)

        if not isinstance(raw, dict):
            raise ValueError(f"Expected dict at top level, got {type(raw)}")

        config = _parse_yaml(raw)
        logger.info(
            "N4 rubric loaded",
            extra={"path": str(rubric_path)},
        )
        return config

    except Exception:
        logger.warning(
            "Failed to parse rubric file — using hardcoded defaults",
            extra={"path": str(rubric_path)},
            exc_info=True,
        )
        return RubricConfig()
