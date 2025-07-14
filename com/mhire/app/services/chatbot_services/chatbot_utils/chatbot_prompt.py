class ChatbotPrompt:
    
    # Emergency keywords that trigger escalation
    EMERGENCY_KEYWORDS = [
        "chest pain", "heart attack", "stroke", "can't breathe", "difficulty breathing",
        "severe bleeding", "heavy bleeding", "unconscious", "overdose", "suicide",
        "suicidal", "self-harm", "emergency", "911", "ambulance", "dying",
        "severe allergic reaction", "anaphylaxis", "choking", "seizure",
        "severe head injury", "broken bone", "compound fracture", "continuous bleeding"
    ]
    
    # High priority keywords
    HIGH_PRIORITY_KEYWORDS = [
        "severe pain", "high fever", "vomiting blood", "blood in stool",
        "severe headache", "confusion", "dizziness", "fainting",
        "severe abdominal pain", "shortness of breath", "rapid heartbeat"
    ]
    
    # Appointment booking keywords
    APPOINTMENT_KEYWORDS = [
        "book appointment", "schedule appointment", "need appointment", "make appointment",
        "see doctor", "visit", "consultation", "check up", "appointment"
    ]

    @staticmethod
    def get_system_prompt(organization_type: str) -> str:
        """Get organization-specific system prompt"""
        
        base_prompt = """You are a medical triage assistant. Your role is to:
1. Provide general health guidance and information
2. Help with symptom intake and assessment  
3. Route users to appropriate care levels
4. Collect appointment booking information when requested

IMPORTANT LIMITATIONS:
- You cannot provide diagnoses or specific medical treatments
- You cannot prescribe medications
- You cannot replace professional medical advice
- Always recommend consulting healthcare providers for medical concerns

When users mention symptoms or want appointments, ask relevant follow-up questions."""

        if organization_type == "HRH":
            return base_prompt + """

TONE (HRH - Health Resource Hub):
- Use professional, clinical language
- Ask detailed medical questions
- Use medical terminology when appropriate
- Maintain formal, respectful communication"""

        else:  # SMB
            return base_prompt + """

TONE (SMB - Small Medical Business):
- Use friendly, conversational language
- Focus on wellness and preventive care
- Make questions easy to understand
- Maintain warm, empathetic communication"""

    @staticmethod
    def get_appointment_questions():
        """Questions to ask for appointment booking"""
        return [
            "What would you like to schedule an appointment for?",
            "When would you prefer to come in? (date and time)",
            "Is this urgent or can it wait for a regular appointment?",
            "Do you have any location preference?",
            "What's the best way to contact you for confirmation?"
        ]