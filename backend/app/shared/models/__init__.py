from app.shared.models.activity import Activity, ActivityStatus
from app.shared.models.commission import Commission
from app.shared.models.course import Course
from app.shared.models.enrollment import Enrollment
from app.shared.models.event_outbox import EventOutbox
from app.shared.models.exercise import Exercise, ExerciseDifficulty
from app.shared.models.llm_config import LLMConfig, LLMProvider
from app.shared.models.user import User, UserRole

# Feature models — imported here so Alembic's Base.metadata sees them
from app.features.submissions.models import ActivitySubmission, CodeSnapshot, Submission  # noqa: E402
from app.features.tutor.models import InteractionRole, TutorInteraction, TutorSystemPrompt  # noqa: E402
from app.features.governance.models import GovernanceEvent  # noqa: E402
from app.features.cognitive.models import CognitiveSession, CognitiveEvent  # noqa: E402
from app.features.evaluation.models import CognitiveMetrics, ReasoningRecord  # noqa: E402
from app.features.risk.models import RiskAssessment  # noqa: E402

__all__ = [
    "Activity",
    "ActivityStatus",
    "Commission",
    "Course",
    "Enrollment",
    "EventOutbox",
    "Exercise",
    "ExerciseDifficulty",
    "LLMConfig",
    "LLMProvider",
    "User",
    "UserRole",
    # Submissions
    "ActivitySubmission",
    "CodeSnapshot",
    "Submission",
    # Tutor
    "InteractionRole",
    "TutorInteraction",
    "TutorSystemPrompt",
    # Governance
    "GovernanceEvent",
    # Cognitive
    "CognitiveSession",
    "CognitiveEvent",
    # Evaluation
    "CognitiveMetrics",
    "ReasoningRecord",
    # Risk
    "RiskAssessment",
]
