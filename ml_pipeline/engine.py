def calculate_vishing_risk(acoustic_features, text_analysis):
    """
    Combines sensory outputs from acoustic profiles and NLP context 
    to output a unified threat score.
    """
    acoustic_risk = 0.4 if acoustic_features["is_synthetic_heuristic"] else 0.0
    text_risk = text_analysis["intent_confidence"] if text_analysis["is_malicious_intent"] else 0.0
    
    # Weightings: Text intent holds higher weight for immediate fraud signaling (60% text / 40% audio)
    final_score = (text_risk * 0.6) + (acoustic_risk * 0.4)
    
    # Determine overall status
    if final_score > 0.75:
        status = "CRITICAL_CRIME_SUSPECTED"
    elif final_score > 0.4:
        status = "WARNING_SUSPICIOUS_ACTIVITY"
    else:
        status = "SAFE"
        
    return {
        "risk_score": round(final_score * 100, 2),
        "status": status,
        "indicators": {
            "synthetic_voice_detected": acoustic_features["is_synthetic_heuristic"],
            "flagged_intent": text_analysis["dominant_intent"]
        }
    }