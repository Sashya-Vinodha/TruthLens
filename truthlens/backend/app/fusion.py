# backend/app/fusion.py
# Simple fusion rules to combine verifier output into confidence + abstain decision

from typing import Dict, Any

# Tunable thresholds
ABSTAIN_THRESHOLD = 0.5   # if overall_support < this -> abstain
UNSUPPORTED_FRAC_ABORT = 0.4  # if fraction of unsupported claims > this -> abstain

def fuse(verifier_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Input: verifier_output (dict with 'claims' list and 'overall_support' float)
    Returns: dict { "confidence": float (0..1), "abstain": bool }
    """
    claims = verifier_output.get("claims", [])
    overall = float(verifier_output.get("overall_support", 0.0))

    if not claims:
        return {"confidence": 0.0, "abstain": True}

    unsupported = sum(1 for c in claims if not c.get("supported", False))
    unsup_frac = unsupported / len(claims)

    # Base confidence from overall support, penalize by unsupported fraction
    confidence = max(0.0, overall * (1.0 - 0.5 * unsup_frac))
    confidence = min(1.0, confidence)

    abstain = (overall < ABSTAIN_THRESHOLD) or (unsup_frac > UNSUPPORTED_FRAC_ABORT)

    return {"confidence": round(confidence, 4), "abstain": bool(abstain)}
