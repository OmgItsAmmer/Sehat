"""Pediatric intake — child symptoms and vitals context."""

SYSTEM_PROMPT = """
You are a pediatric intake assistant. Gather these fields in natural conversation.
Ask one question at a time. Use simple language for parents or guardians.
"""

REQUIRED_SLOTS: tuple[str, ...] = (
    "child_age",
    "child_weight",
    "fever_duration",
    "chief_symptoms",
    "contact_phone",
    "preferred_day",
)

SLOT_QUESTIONS: dict[str, str] = {
    "child_age": "How old is the child (months or years)?",
    "child_weight": "Roughly how much does the child weigh (kg is fine)?",
    "fever_duration": "If there is fever, how long has it lasted?",
    "chief_symptoms": "What symptoms are you most worried about right now?",
    "contact_phone": (
        "Please share the mobile number we should use for your appointment (e.g. 03XXXXXXXXX)."
    ),
    "preferred_day": "Which day works best for a pediatric appointment?",
}
