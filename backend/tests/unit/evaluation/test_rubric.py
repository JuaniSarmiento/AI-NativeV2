"""Unit tests for the rubric loader.

Tests:
  - Loading from the real YAML file
  - Loading with a custom path
  - Graceful fallback when file is missing
  - Graceful fallback when YAML is malformed
  - Typed values match expected defaults
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from app.features.evaluation.rubric import (
    RubricConfig,
    RubricWeights,
    RiskThresholds,
    QualityFactors,
    load_rubric,
)


class TestDefaultRubric:
    def test_default_rubric_config_has_correct_weights(self) -> None:
        config = RubricConfig()
        w = config.weights
        assert w.n1_comprehension == 0.15
        assert w.n2_strategy == 0.25
        assert w.n3_validation == 0.25
        assert w.n4_ai_interaction == 0.20
        assert w.qe == 0.15

    def test_weights_sum_to_one(self) -> None:
        config = RubricConfig()
        w = config.weights
        total = w.n1_comprehension + w.n2_strategy + w.n3_validation + w.n4_ai_interaction + w.qe
        assert abs(total - 1.0) < 1e-9

    def test_default_risk_thresholds_critical(self) -> None:
        config = RubricConfig()
        crit = config.risk_thresholds.critical
        assert crit.dependency_score_min == 0.7
        assert crit.n4_score_max == 30

    def test_default_risk_thresholds_high(self) -> None:
        config = RubricConfig()
        high = config.risk_thresholds.high
        assert high.dependency_score_min == 0.5
        assert high.any_n_score_max == 20

    def test_default_risk_thresholds_medium(self) -> None:
        config = RubricConfig()
        med = config.risk_thresholds.medium
        assert med.any_n_score_max == 40


class TestRubricFileLoading:
    def test_load_rubric_from_real_yaml(self) -> None:
        """The actual rubrics/n4_anexo_b.yaml should parse successfully."""
        config = load_rubric()
        assert isinstance(config, RubricConfig)
        assert isinstance(config.weights, RubricWeights)
        assert isinstance(config.risk_thresholds, RiskThresholds)
        assert isinstance(config.quality_factors, QualityFactors)

    def test_real_yaml_weights_match_defaults(self) -> None:
        """Loaded YAML should produce the same weights as the hardcoded defaults."""
        config = load_rubric()
        assert config.weights.n1_comprehension == 0.15
        assert config.weights.n2_strategy == 0.25
        assert config.weights.n3_validation == 0.25
        assert config.weights.n4_ai_interaction == 0.20
        assert config.weights.qe == 0.15

    def test_real_yaml_quality_factors_n1_events(self) -> None:
        config = load_rubric()
        assert "reads_problem" in config.quality_factors.n1.events
        assert "code.snapshot" in config.quality_factors.n1.events

    def test_real_yaml_n4_dependency_penalty(self) -> None:
        config = load_rubric()
        assert config.quality_factors.n4.dependency_penalty == 0.3


class TestRubricFallbackBehavior:
    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        """A path that does not exist should return default RubricConfig."""
        missing = tmp_path / "nonexistent.yaml"
        config = load_rubric(path=missing)
        assert isinstance(config, RubricConfig)
        # Weights should match defaults
        assert config.weights.n1_comprehension == 0.15

    def test_malformed_yaml_returns_defaults(self, tmp_path: Path) -> None:
        """A file with invalid YAML should return default RubricConfig."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(":: this is not valid yaml ::")
        config = load_rubric(path=bad_yaml)
        assert isinstance(config, RubricConfig)
        assert config.weights.n2_strategy == 0.25

    def test_yaml_with_wrong_type_returns_defaults(self, tmp_path: Path) -> None:
        """A valid YAML file that isn't a dict should return defaults."""
        list_yaml = tmp_path / "list.yaml"
        list_yaml.write_text("- item1\n- item2\n")
        config = load_rubric(path=list_yaml)
        assert isinstance(config, RubricConfig)


class TestCustomYamlLoading:
    def test_custom_weights_parsed_correctly(self, tmp_path: Path) -> None:
        """Custom YAML weights should override hardcoded defaults."""
        custom = tmp_path / "custom.yaml"
        custom.write_text(
            textwrap.dedent(
                """
                weights:
                  n1_comprehension: 0.10
                  n2_strategy: 0.30
                  n3_validation: 0.30
                  n4_ai_interaction: 0.20
                  qe: 0.10
                risk_thresholds:
                  critical:
                    dependency_score_min: 0.8
                    n4_score_max: 25
                  high:
                    dependency_score_min: 0.6
                    any_n_score_max: 15
                  medium:
                    any_n_score_max: 35
                    qe_score_max: 35
                quality_factors:
                  n1:
                    events: ["reads_problem"]
                    min_engagement_seconds: 5
                  n2:
                    events: ["submission.created"]
                    requires_prior: ["code.run"]
                  n3:
                    events: ["code.run"]
                    requires_correction: true
                  n4:
                    events: ["tutor.question_asked"]
                    dependency_penalty: 0.4
                """
            )
        )
        config = load_rubric(path=custom)
        assert config.weights.n1_comprehension == 0.10
        assert config.weights.n2_strategy == 0.30
        assert config.risk_thresholds.critical.dependency_score_min == 0.8
        assert config.risk_thresholds.critical.n4_score_max == 25
        assert config.quality_factors.n4.dependency_penalty == 0.4
        assert "reads_problem" in config.quality_factors.n1.events

    def test_partial_yaml_fills_missing_with_none(self, tmp_path: Path) -> None:
        """A YAML file with only weights section should still parse."""
        partial = tmp_path / "partial.yaml"
        partial.write_text("weights:\n  n1_comprehension: 0.20\n  n2_strategy: 0.20\n  n3_validation: 0.20\n  n4_ai_interaction: 0.20\n  qe: 0.20\n")
        config = load_rubric(path=partial)
        assert config.weights.n1_comprehension == 0.20
        # Risk thresholds missing → use defaults from dataclass
        assert isinstance(config.risk_thresholds, RiskThresholds)
