def analyze_text_baseline(transcript):
    """
    A foundational text analyzer that flags high-risk vishing keywords.
    """
    # Convert text to lowercase so capitalization doesn't confuse our check
    clean_text = transcript.lower()
    
    # Define simple lists of phrases phone scammers frequently use
    urgency_keywords = ["immediately", "transfer now", "urgently", "account suspended"]
    credential_keywords = ["password", "otp", "verification code", "pin number"]
    
    # Check if any scam phrases exist in the conversation text
    has_urgency = any(word in clean_text for word in urgency_keywords)
    has_credential_request = any(word in clean_text for word in credential_keywords)
    
    # If it contains scam phrases, mark it as suspicious
    if has_urgency or has_credential_request:
        return "WARNING: Suspicious Activity Detected"
    
    return "SAFE: Standard Conversation"

# --- TEMPORARY TEST LINES ---
test_call_1 = "Hey, are we still meeting up for lunch at the cafe today?"
test_call_2 = "This is your bank! Give me your password and OTP immediately or your account is suspended!"

print("Testing Call 1:", analyze_text_baseline(test_call_1))
print("Testing Call 2:", analyze_text_baseline(test_call_2))