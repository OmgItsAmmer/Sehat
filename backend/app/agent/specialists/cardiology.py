"""Cardiac intake — chest pain and cardiovascular red flags."""

SYSTEM_PROMPT = """
You are a cardiac intake assistant. Gather these fields in natural conversation.
Ask one question at a time. Be calm and reassuring.
"""

REQUIRED_SLOTS: tuple[str, ...] = (
    "pain_location",
    "pain_radiation",
    "onset",
    "associated_symptoms",
    "medical_history",
    "contact_phone",
    "preferred_day",
)

SLOT_QUESTIONS: dict[str, str] = {
    "pain_location": "Where exactly is the pain or discomfort (chest, left arm, jaw, etc.)?",
    "pain_radiation": "Does the pain spread anywhere else, such as your arm, jaw, or back?",
    "onset": "Did it start suddenly or gradually?",
    "associated_symptoms": "Any sweating, nausea, breathlessness, or dizziness with it?",
    "medical_history": "Any prior heart problems, stents, or heart attacks in you or close family?",
    "contact_phone": (
        "Please share the mobile number we should use for your appointment (e.g. 03XXXXXXXXX)."
    ),
    "preferred_day": "Which day works best for an appointment (e.g. Monday, Wednesday)?",
}
