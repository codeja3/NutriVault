import pytest

from src.advisory import (
    CLINICAL_DISCLAIMER_TEXT,
    FITNESS_ADVISORY_WIRE_TEXT,
    ClinicalAdvisoryViolationError,
    generate_athletic_targets,
    validate_goal_generation_eligibility,
)
from src.db import Profile


def test_clinical_hard_lock_on_chronic_condition():
    """Profiles marked chronic_condition must raise ClinicalAdvisoryViolationError."""
    profile = Profile(
        id="p_crohns",
        name="Charlie",
        birth_date="1985-02-10",
        profile_type="chronic_condition",
        condition_notes="Crohn's Disease (Remission)",
    )

    with pytest.raises(ClinicalAdvisoryViolationError) as exc_info:
        validate_goal_generation_eligibility(profile)

    assert exc_info.value.error_code == "ERR_CLINICAL_AI_RESTRICTED"
    assert CLINICAL_DISCLAIMER_TEXT in exc_info.value.disclaimer
    assert "Nutritional goals for chronic conditions must be established" in str(exc_info.value)


def test_standard_and_athletic_eligibility():
    """Standard and athletic profiles pass eligibility validation."""
    standard_profile = Profile(
        id="p_std",
        name="Alice",
        birth_date="1992-04-01",
        profile_type="standard",
        condition_notes=None,
    )
    athletic_profile = Profile(
        id="p_ath",
        name="Bob",
        birth_date="1990-08-20",
        profile_type="athletic",
        condition_notes="Marathon runner",
    )

    # Should not raise
    validate_goal_generation_eligibility(standard_profile)
    validate_goal_generation_eligibility(athletic_profile)


def test_generate_athletic_targets_with_advisory_wire():
    """Athletic target generation must bundle the exact mandatory advisory wire text."""
    profile = Profile(
        id="p_ath",
        name="Bob",
        birth_date="1990-08-20",
        profile_type="athletic",
        condition_notes="Marathon runner",
    )

    response = generate_athletic_targets(
        profile=profile,
        athletic_goal="endurance",
        weight_kg=70.0,
    )

    assert response.calories_target > 0
    assert response.protein_g_target > 0
    assert response.carbs_g_target > 0
    assert response.fat_g_target > 0
    assert response.fiber_g_target > 0

    # Mandatory advisory wire assertion
    assert response.advisory_wire == FITNESS_ADVISORY_WIRE_TEXT
    assert "certified fitness trainer" in response.advisory_wire
    assert "search.brave.com/ask" in response.advisory_wire
    assert response.requires_acknowledgment is True


def test_generate_athletic_targets_blocked_for_chronic_condition():
    """generate_athletic_targets must enforce the clinical hard lock directly."""
    chronic_profile = Profile(
        id="p_ckd",
        name="Dan",
        birth_date="1978-11-05",
        profile_type="chronic_condition",
        condition_notes="CKD Stage 2",
    )

    with pytest.raises(ClinicalAdvisoryViolationError) as exc_info:
        generate_athletic_targets(
            profile=chronic_profile,
            athletic_goal="hypertrophy",
            weight_kg=80.0,
        )

    assert exc_info.value.error_code == "ERR_CLINICAL_AI_RESTRICTED"
