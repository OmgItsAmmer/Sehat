"""General clinic intake — routine appointments and non-specialty complaints."""

SYSTEM_PROMPT = """
You are a general clinic intake assistant. Gather these fields in natural conversation.
Ask one question at a time. Be warm and concise.
"""

REQUIRED_SLOTS: tuple[str, ...] = (
    "chief_complaint",
    "symptom_duration",
    "contact_phone",
    "preferred_day",
)

SLOT_QUESTIONS: dict[str, str] = {
    "chief_complaint": "What is the main problem or symptom we should know about?",
    "symptom_duration": "How long have you had this (hours, days, or weeks)?",
    "contact_phone": (
        "Please share the mobile number we should use for your appointment (e.g. 03XXXXXXXXX)."
    ),
    "preferred_day": "Which day works best for an appointment (e.g. Monday, Wednesday)?",
}
