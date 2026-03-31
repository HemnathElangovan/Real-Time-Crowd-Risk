import config

LOW    = "LOW"
MEDIUM = "MEDIUM"
HIGH   = "HIGH"

RISK_COLOR = {
    LOW:    "#22c55e",
    MEDIUM: "#f59e0b",
    HIGH:   "#ef4444",
}

RISK_BGR = {
    LOW:    (50, 205, 50),
    MEDIUM: (30, 165, 255),
    HIGH:   (30,  30, 230),
}

RISK_MSG = {
    LOW:    "Crowd level is normal. No action required.",
    MEDIUM: "Crowd is building up. Send personnel to monitor the area.",
    HIGH:   "CRITICAL — Crowd density dangerously high. Immediate deployment required.",
}

def classify(count: int):
    if count <= config.LOW_MAX:
        return LOW
    elif count <= config.MEDIUM_MAX:
        return MEDIUM
    return HIGH
