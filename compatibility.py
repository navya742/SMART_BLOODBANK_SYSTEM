"""
Biological compatibility rules and domain constants kept separate from
allocation logic so rules can be maintained independently.
"""

URGENCY_WEIGHTS = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MODERATE": 2,
    "ROUTINE": 1,
}

BLOOD_GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
COMPONENT_TYPES = ["RBC", "Plasma", "Platelets"]

# Recipient -> Ordered list of compatible donor blood groups
# Exact match is attempted first; specific donors are tried before universal O-
COMPATIBILITY_MAP = {
    "O-": ["O-"],
    "O+": ["O+", "O-"],
    "A-": ["A-", "O-"],
    "A+": ["A+", "A-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "AB-": ["AB-", "A-", "B-", "O-"],
    "AB+": ["AB+", "AB-", "A+", "A-", "B+", "B-", "O+", "O-"],
}


def get_compatible_donors(recipient_group: str) -> list:
    """Return ordered donor groups starting with exact match, then compatible fallbacks."""
    recipient = recipient_group.strip().upper()
    compatible = COMPATIBILITY_MAP.get(recipient, [recipient])
    return [recipient] + [g for g in compatible if g != recipient]