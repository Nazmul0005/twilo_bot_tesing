import logging

logger = logging.getLogger(__name__)

# Human escalation keywords - urgent medical situations
HUMAN_ESCALATION_KEYWORDS = [
    "urgent", "help", "real person", "live agent", "chest pain", 
    "continuous bleeding", "severe bleeding", "can't breathe", 
    "difficulty breathing", "unconscious", "emergency", "911",
    "severe pain", "heart attack", "stroke", "allergic reaction",
    "overdose", "suicide", "self harm", "major injury", "trauma",
    "severe headache", "vision loss", "paralysis", "seizure"
]

# Appointment escalation keywords - scheduling related
APPOINTMENT_ESCALATION_KEYWORDS = [
    "book", "schedule", "doctor", "consult", "appointment",
    "visit", "see a doctor", "clinic", "booking", "available",
    "when can i", "make appointment", "schedule visit",
    "book appointment", "see physician", "consultation"
]

def check_escalation_keywords(message: str) -> tuple[bool, bool]:
    """
    Check if message contains escalation keywords
    Returns: (human_escalation, appointment_escalation)
    """
    logger.debug(f"Checking escalation keywords for message: {message[:50]}...")
    
    message_lower = message.lower()
    
    # Check for human escalation first (higher priority)
    human_escalation = any(keyword in message_lower for keyword in HUMAN_ESCALATION_KEYWORDS)
    logger.debug(f"Human escalation detected: {human_escalation}")
    
    # Check for appointment escalation
    appointment_escalation = any(keyword in message_lower for keyword in APPOINTMENT_ESCALATION_KEYWORDS)
    logger.debug(f"Appointment escalation detected: {appointment_escalation}")
    
    return human_escalation, appointment_escalation