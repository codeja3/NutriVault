"""Advisory safeguards, clinical hard lock, and athletic recommendation engine."""

from dataclasses import dataclass

from src.db import Profile

CLINICAL_DISCLAIMER_TEXT = (
    "Nutritional goals for chronic conditions must be established in consultation with a "
    "qualified physician or registered dietitian. NutriVault does not provide clinical "
    "diagnoses or therapeutic prescriptions."
)

FITNESS_ADVISORY_WIRE_TEXT = (
    "Local model fitness baselines are heuristic estimates. For rigorous training regimens or "
    "metabolic adjustments, consult a certified fitness trainer or cross-reference using "
    "privacy-preserving frontier endpoints (e.g., search.brave.com/ask)."
)


class ClinicalAdvisoryViolationError(PermissionError):
    """Raised when AI goal generation is attempted on a chronic condition profile."""

    def __init__(self, message: str | None = None):
        self.error_code = "ERR_CLINICAL_AI_RESTRICTED"
        self.disclaimer = CLINICAL_DISCLAIMER_TEXT
        super().__init__(message or self.disclaimer)


@dataclass(frozen=True)
class AthleticAdvisoryResponse:
    calories_target: int
    protein_g_target: float
    carbs_g_target: float
    fat_g_target: float
    fiber_g_target: float
    advisory_wire: str
    requires_acknowledgment: bool = True


def validate_goal_generation_eligibility(profile: Profile) -> None:
    """Validate that the profile is allowed to receive automated AI dietary targets."""
    if profile.profile_type == "chronic_condition":
        raise ClinicalAdvisoryViolationError()


def generate_athletic_targets(
    profile: Profile,
    athletic_goal: str,
    weight_kg: float,
) -> AthleticAdvisoryResponse:
    """Generate heuristic athletic target envelopes with mandatory trainer advisory wire."""
    validate_goal_generation_eligibility(profile)

    goal = athletic_goal.lower()
    if goal == "endurance":
        protein_g = round(weight_kg * 1.5, 1)
        carbs_g = round(weight_kg * 6.5, 1)
        fat_g = round(weight_kg * 1.0, 1)
        fiber_g = 35.0
    elif goal == "hypertrophy":
        protein_g = round(weight_kg * 2.0, 1)
        carbs_g = round(weight_kg * 4.5, 1)
        fat_g = round(weight_kg * 1.0, 1)
        fiber_g = 38.0
    else:
        protein_g = round(weight_kg * 1.6, 1)
        carbs_g = round(weight_kg * 4.0, 1)
        fat_g = round(weight_kg * 1.0, 1)
        fiber_g = 32.0

    calories = int(round((protein_g * 4.0) + (carbs_g * 4.0) + (fat_g * 9.0)))

    return AthleticAdvisoryResponse(
        calories_target=calories,
        protein_g_target=protein_g,
        carbs_g_target=carbs_g,
        fat_g_target=fat_g,
        fiber_g_target=fiber_g,
        advisory_wire=FITNESS_ADVISORY_WIRE_TEXT,
        requires_acknowledgment=True,
    )
