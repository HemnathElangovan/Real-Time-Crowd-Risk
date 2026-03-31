# risk_classifier.py — risk level logic
import config

LOW    = "LOW"
MEDIUM = "MEDIUM"
HIGH   = "HIGH"

RISK_COLORS = {
    LOW:    (34,  197,  94),   # green  (RGB for frontend)
    MEDIUM: (251, 146,  60),   # amber
    HIGH:   (239,  68,  68),   # red
}

RISK_CV_COLORS = {            # BGR for OpenCV
    LOW:    (50,  200,  50),
    MEDIUM: (30,  140, 255),
    HIGH:   (30,   30, 230),
}

RISK_HEX = {
    LOW:    "#22c55e",
    MEDIUM: "#fb923c",
    HIGH:   "#ef4444",
}

RISK_MESSAGES = {
    LOW:    "Crowd level normal. Monitoring active.",
    MEDIUM: "Crowd density building. Deploy personnel to monitor the area.",
    HIGH:   "CRITICAL — Crowd density dangerously high. Immediate deployment required. Risk of crush.",
}

def classify_risk(count: int) -> tuple:
    if count <= config.LOW_MAX:
        return LOW,    RISK_CV_COLORS[LOW]
    elif count <= config.MEDIUM_MAX:
        return MEDIUM, RISK_CV_COLORS[MEDIUM]
    else:
        return HIGH,   RISK_CV_COLORS[HIGH]
