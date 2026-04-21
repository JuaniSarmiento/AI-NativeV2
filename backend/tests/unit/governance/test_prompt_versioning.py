"""Tests for semantic prompt version validation (B7)."""
from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.features.governance.service import GovernanceService


class TestValidatePromptVersion:
    def test_major_increment_valid(self) -> None:
        GovernanceService.validate_prompt_version("3.0.0", "2.1.3", "major")

    def test_major_increment_from_none(self) -> None:
        GovernanceService.validate_prompt_version("1.0.0", None, "major")

    def test_major_increment_wrong(self) -> None:
        with pytest.raises(ValidationError, match="version"):
            GovernanceService.validate_prompt_version("2.1.0", "2.0.0", "major")

    def test_minor_increment_valid(self) -> None:
        GovernanceService.validate_prompt_version("2.2.0", "2.1.3", "minor")

    def test_minor_increment_wrong_major(self) -> None:
        with pytest.raises(ValidationError, match="version"):
            GovernanceService.validate_prompt_version("3.0.0", "2.1.0", "minor")

    def test_minor_increment_wrong_minor(self) -> None:
        with pytest.raises(ValidationError, match="version"):
            GovernanceService.validate_prompt_version("2.3.0", "2.1.0", "minor")

    def test_patch_increment_valid(self) -> None:
        GovernanceService.validate_prompt_version("2.1.4", "2.1.3", "patch")

    def test_patch_increment_wrong(self) -> None:
        with pytest.raises(ValidationError, match="version"):
            GovernanceService.validate_prompt_version("2.1.5", "2.1.3", "patch")

    def test_patch_major_changed(self) -> None:
        with pytest.raises(ValidationError, match="version"):
            GovernanceService.validate_prompt_version("3.1.4", "2.1.3", "patch")

    def test_invalid_change_type(self) -> None:
        with pytest.raises(ValidationError, match="Invalid change_type"):
            GovernanceService.validate_prompt_version("1.0.0", None, "hotfix")

    def test_invalid_version_format(self) -> None:
        with pytest.raises(ValidationError, match="not valid semver"):
            GovernanceService.validate_prompt_version("v1.0", None, "major")

    def test_previous_invalid_format_skips_validation(self) -> None:
        GovernanceService.validate_prompt_version("1.0.0", "not-semver", "major")
